import logging


class Logger:
    """
    A simple logger class.
    """

    _loggers = {}

    @staticmethod
    def get_logger(name="HandGhost"):
        """
        Gets a logger instance.

        Args:
            name: The name of the logger.

        Returns:
            A logger instance.
        """
        if name not in Logger._loggers:
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(name)
            Logger._loggers[name] = logger
        return Logger._loggers[name]
