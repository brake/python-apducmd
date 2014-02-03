# -*- coding: UTF-8 -*-
#-------------------------------------------------------------------------------
# Copyright:  (c) Constantin Roganov, 2014
# Licence:    <your licence>
#-------------------------------------------------------------------------------

"""Command shell with ability to execute APDU just like commands and see
SW and output data on the screen.
"""

import sys
import cmd
import msvcrt

from smartcard.CardConnection import CardConnection, CardConnectionEvent
from smartcard.Observer import Observable
from smartcard.CardMonitoring import CardMonitor
from smartcard.System import readers
from smartcard.util import toBytes, toHexString, PACK


def select_reader():
    """Select cardreader with console onscreen menu.
    Returns selected reader object or None if no readers connected or user
    decided to escape shell.
    If system has a single reader connected it will be returned without of
    menu drawing.
    """
    readers_list = readers()

    if not readers_list:
        return

    if len(readers_list) == 1:
        return readers_list[0]

    else:
        print 'Please choose reader number from list or 0 to exit:\n\n'

        for i, r in enumerate(readers_list):
            print '[{}] - {}\n'.format(i + 1, r)

        print '\n[0] - Exit without choosing\n'

        choice = None
        while not msvcrt.kbhit():
            choice = msvcrt.getche()

            if not choice.isdigit():
                continue

            if choice == '0':
                return

            try:
                return readers_list[int(choice) - 1]

            except IndexError:
                pass


class APDUShell(cmd.Cmd):
    """Command shell to communicate with smartcard via APDU.

    Reader selection will be performed on shell start.
    Prompt will contain a selected reader's name and FID of latest selected EF or DF.
    Response data and SW for each APDU will be printed in console.
    """

    def __init__(self, *args, **kwargs):
        # base classes are old style classes so super() not allowed here
        cmd.Cmd.__init__(self, *args, **kwargs)

        self.reader = select_reader()
        self.card = None
        self.connection = None
        self.sel_obj = ''
        self.card_monitor = CardMonitor()
        self.card_monitor.addObserver(self)

    def _card_observer_update(self, observable, (addedcards, removedcards)):
        """CardObserver interface implementation"""

        if self.card and self.card in removedcards:
            self.sel_obj = ''
            self.card = None
            self.connection = None

        for card in addedcards:
            if card.reader == self.reader:
                self.card = card
                self._set_up_connection()
                break

    def _card_connection_observer_update(self, card_connection, event):
        """CardConnectionObserver interface implementation"""

        if 'connect' == event.type:
            print 'Card inserted\n'

        elif 'disconnect' == event.type:
            print 'Card removed\n'

        elif 'command' == event.type:
            print '> ', toHexString(event.args[0])

        elif 'response' == event.type:
            print '< ', '[{}]\n<  {:02X} {:02X}\n'.format(toHexString(event.args[0]), *event.args[1:])

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

            # if INS is A4 (SELECT) then catch and save FID
            if apdu[1] != 0xA4:
                return

            self.sel_obj = toHexString(apdu[5:], PACK)

        except TypeError as e:
            print e.message

    def do_exit(self, arg):
        return True

    def preloop(self):
        """Try to connect to cardreader.
        If connection does not set then exit program.
        """

        if self.reader is None:
            sys.exit()

        self.postcmd(None, None)

    def postcmd(self, stop, line):
        """Print the command prompt"""

        if self.card is None:
            self.prompt = 'Please insert card into reader [{}]>'.format(self.reader)

        else:
            self.prompt = 'Using reader [{}]\n[{}] selected>'.format(self.reader, self.sel_obj or 'None')

        return stop

    def _set_up_connection(self):
        """Create & configure a new card connection"""

        self.connection = self.card.createConnection()
        self.connection.addObserver(self)
        self.connection.connect()


if __name__ == '__main__':
    apdu_sh = APDUShell()
    apdu_sh.cmdloop()