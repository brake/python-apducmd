# -*- coding: UTF-8 -*-
# ------------------------------------------------------------------------------
# Copyright © Constantin Roganov, 2014-2017
# Licence:  MIT
# ------------------------------------------------------------------------------

"""Command shell with ability to execute APDU just like commands and see
SW and output data on the screen.
"""

import sys
import cmd
import locale

from smartcard.CardConnection import CardConnection, CardConnectionEvent
from smartcard.Observer import Observable
from smartcard.CardMonitoring import CardMonitor
from smartcard.System import readers
from smartcard.util import toBytes, toHexString, PACK
from smartcard.Exceptions import CardConnectionException


def select_reader():
    """Select the first of available readers.
    Return smartcard.reader.Reader or None if no readers attached.
    """
    readers_list = readers()

    if readers_list:
        return readers_list[0]


class APDUShell(cmd.Cmd):
    """Command shell to communicate with smartcard via APDU.

    Reader selection will be performed on shell start.
    Prompt will contain a selected reader's name and FID of latest selected EF or DF.
    Response data and SW for each APDU will be printed in console.

    Additional commands are:
        exit - exit shell
        atr - print connected card's ATR as a hex string
    """

    SELECT_COMMAND_INSTRUCTION = 0xA4
    SELECT_SUCCESSFUL_SW1 = (0x90, 0x9E, 0x9F, 0x61)

    intro = """Command shell to communicate with smart card using APDU.
    Type APDU as a hex string.
    Use 'exit' command to leave shell.
    Use 'atr' command to print card's ATR.  
    """

    def __init__(self):
        if sys.version_info.major == 2:
            cmd.Cmd.__init__(self, completekey=None)
        else:
            super(APDUShell, self).__init__(completekey=None)

        self.reader = select_reader()
        self.card = None
        self.connection = None
        self.sel_obj = ''
        self.atr = None
        self.card_monitor = CardMonitor()
        self.card_monitor.addObserver(self)

    def _card_observer_update(self, observable, handlers):
        """CardObserver interface implementation"""

        addedcards, removedcards = handlers

        if self.card and self.card in removedcards:
            self._clear_connection()

        for card in addedcards:
            if str(card.reader) == str(self.reader):
                self.card = card
                self._set_up_connection()
                break

    def _card_connection_observer_update(self, card_connection, event):
        """CardConnectionObserver interface implementation"""

        if 'connect' == event.type:
            message = 'Card inserted'

        elif 'disconnect' == event.type:
            message = 'Card removed'

        elif 'command' == event.type:
            message = '> ' + toHexString(event.args[0])

        elif 'response' == event.type:
            message = '< [{}]\n<  {:02X} {:02X}'.format(toHexString(event.args[0]), *event.args[1:])

        else:
            message = 'Unknown event type: {}'.format(event.type)

        print(message)

    def update(self, *args):
        """Dispatch a call between CardObserver and CardConnectionObserver interfaces
        based on type of arguments.
        If nothing matches raise TypeError.
        """
        if issubclass(args[0].__class__, Observable) and isinstance(args[1], tuple):
            return self._card_observer_update(*args)

        elif issubclass(args[0].__class__, CardConnection) and isinstance(args[1], CardConnectionEvent):
            return self._card_connection_observer_update(*args)

        else:
            raise TypeError('Can not dispatch a call due to incorrect arguments')

    def default(self, line):
        """Process all APDU"""

        if not line or self.card is None:
            return

        try:
            apdu = toBytes(line)
            data, sw1, sw2 = self.connection.transmit(apdu)

            # if INS is A4 (SELECT) then catch and save FID if select is successful
            if apdu[1] != APDUShell.SELECT_COMMAND_INSTRUCTION or sw1 not in APDUShell.SELECT_SUCCESSFUL_SW1:
                return

            self.sel_obj = toHexString(apdu[5:], PACK)

        except (TypeError, CardConnectionException) as e:
            try:
                print(e.message.decode(locale.getpreferredencoding()))
            except AttributeError:
                print(e.__class__.__name__ + ' (no message given)')

    def do_exit(self, _):
        """React on 'exit' command"""
        print('Bye!\n')

        return True

    def do_atr(self, _):
        """React on 'atr' command, print current card's ATR"""
        if self.atr:
            print(self.atr)
        else:
            print('Error: Card connection not found')

    def preloop(self):
        """Try to connect to cardreader.
        If connection does not set then exit program.
        """

        if self.reader is None:
            print('\nError: Unable to connect to card reader\n')
            sys.exit()

        self.postcmd(None, None)

    def postcmd(self, stop, line):
        """Print the command prompt"""

        if self.card is None:
            self.prompt = 'Please insert card into reader [{}]> '.format(self.reader)

        else:
            self.prompt = 'Using reader [{}]\n[{}] selected> '.format(self.reader, self.sel_obj or 'None')

        return stop

    def _set_up_connection(self):
        """Create & configure a new card connection"""

        self.connection = self.card.createConnection()
        self.connection.addObserver(self)
        self.connection.connect()
        self.atr = toHexString(self.connection.getATR(), PACK)

    def _clear_connection(self):
        self.self_obj = ''
        self.card = None
        self.connection = None
        self.atr = None


if __name__ == '__main__':
    APDUShell().cmdloop()