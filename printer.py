import os
import logging
import shutil

logger = logging.getLogger('photobooth.printer')

class CmdPrinter(object):
    def __init__(self, name, count, debug):
        self.name = name
        self.count = count
        self.debug = debug

    def print_image(self, image_path):
        printing_cmd = ["lpr"]
        if self.name:
            printing_cmd += ["-P", self.printer]
        printing_cmd += ["-#", str(self.count), image_path]

        logger.info(' '.join(printing_cmd))
        if not self.debug:
            call(printing_cmd)
            
    def get_error(self):
        return None

PRINTER_STATES = {
    3: 'Idle',
    4: 'Printing',
    5: 'Off'
}

class PyPrinter(object):
    def __init__(self, name, count, debug):
        import cups
    
        self.connection = cups.Connection()
        self.name = name or self.connection.getDefault()
        self.count = count
        self.debug = debug
        
        logger.info('Using printer: ' + self.name)
        
        if self.name not in self.connection.getPrinters():
            raise Exception("Printer not found: " + str(self.name))

    def get_printer(self):
        return self.connection.getPrinters()[self.name]

    def get_state(self):
        state = self.get_printer()['printer-state']
        
        logger.info('Printer state: %i', state)
        if state not in PRINTER_STATES:
            reason = self.get_printer()['printer-state-reasons']
            message = self.get_printer()['printer-state-message']
            logger.warn('Unknown printer state: %s message %s reason %s', state, message, reason)
        
        return PRINTER_STATES.get(state, 'Unknown')
    
    def get_error(self):
        state = self.get_state()
        if state in ('Idle', 'Printing'):
            return None
        else:
            return state

    def print_image(self, image_path):
        if self.debug:
            logger.info('Would be printing! %s', image_path)
        else:
            try:
                logger.info('Printing: %s', image_path)
                self.connection.printFile(self.name, image_path, image_path, {"copies": str(self.count)})
            except:
                logger.exception("Printing failed for %s", image_path)

class FilePrinter(object):
    def __init__(self):
        logger.info('Using file printer')
        
    def get_error(self):
        return None

    def print_image(self, image_path):
        folder = os.path.join(os.path.dirname(image_path), 'prints')
        if not os.path.exists(folder):
            os.makedirs(folder)
        logger.info('Printing: %s', image_path)
        shutil.copy(image_path, folder)
