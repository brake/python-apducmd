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
from smartcard.CardConnectionObserver import ConsoleCardConnectionObserver


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
        super(APDUShell, self).__init__(completekey=None)

        self.reader = select_reader()
        self._clear_context()
        self.connection = None
        self.card_connection_observer = ConsoleCardConnectionObserver()

        CardMonitor().addObserver(self)

    def update(self, observable, handlers):
        """CardObserver interface implementation"""

        addedcards, removedcards = handlers

        if self.card and self.card in removedcards:
            self._clear_connection()
            self._clear_context()

        for card in addedcards:
            if str(card.reader) == str(self.reader):
                self.card = card
                self._set_up_connection()
                break

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
        self.connection.addObserver(self.card_connection_observer)
        self.connection.connect()
        self.atr = toHexString(self.connection.getATR(), PACK)

    def _clear_connection(self):
        if not self.connection:
            return

        self.connection.deleteObserver(self.card_connection_observer)
        self.connection.disconnect()
        self.connection = None

    def _clear_context(self):
        self.sel_obj = None
        self.card = None
        self.atr = None


if __name__ == '__main__':
    APDUShell().cmdloop()