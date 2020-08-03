from abc import ABCMeta, abstractmethod


class SyncDataBaseBaseclass(metaclass=ABCMeta):

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def write(self, data):
        pass