import collections
import random
import json
from typing import Dict, List
import unittest
import csv
from itertools import cycle, islice, chain, repeat, tee, combinations, permutations, combinations_with_replacement
import re
import logging

# configure logging include in message pattern function name, line number, message, and exception if any
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


class DataProviderStrategy(collections.abc.Iterator):

    def __init__(self, data: List, return_as_dict=False, loop_on_end=True):
        if data is not None and len(data) >= 1:
            self.columns = data[0]
            self.data = data[1:]
        self.return_as_dict = return_as_dict
        self.loop_on_end = loop_on_end
    
    def __iter__(self):
        return self.data.__iter__()

    def __next__(self):
        raise NotImplementedError()

    def format_output(self, el: List) -> Dict or List:
        response = { self.columns[i]: el[i] for i in range(len(el)) }
        new_class = collections.namedtuple("format_output_response",response)
        if self.return_as_dict:
            return response
        else:
            return new_class(**response)
        
    def from_csv(self, path):
        with open(path, "r", newline="") as fd:
            reader = csv.reader(fd)
            self.data = list(reader)
            self.columns = self.data[0]
            self.data = self.data[1:]
    

class RandomDataProviderStrategy(DataProviderStrategy):
    def __init__(self, data: List, return_as_dict=False, loop_on_end=True):
        super().__init__(data, return_as_dict, loop_on_end)
    
    def __next__(self):
        return self.format_output(random.choice(self.data))

class SequentialDataProviderStrategy(DataProviderStrategy):
    def __init__(self, data: List, return_as_dict=False, loop_on_end=True):
        super().__init__(data, return_as_dict, loop_on_end)
        if self.loop_on_end:
            self.it = cycle(self.data)
        else:
            self.it = islice(self.data, 0, None, 1)
    
    def __next__(self):
        return self.format_output(next(self.it))


class UniqueSequentialDataProviderStrategy(DataProviderStrategy):
    def __init__(self, data: List, return_as_dict=False, loop_on_end=True):
        super().__init__(data, return_as_dict, loop_on_end)
    
    def __next__(self):
        return self.format_output(self.data.pop())


class TestStrategiesMethods(unittest.TestCase):
    def __init__(self, methodName: str = ...) -> None:
        super().__init__(methodName)
        self.reset_data()
    
    def reset_data(self):
        with open("./../data/people.csv", "r") as fd:
            self.data = list(csv.reader(fd))
    
    # a method for testing each strategy
    def test_random_strategy(self): 
        data_provider = RandomDataProviderStrategy(self.data, return_as_dict=False, loop_on_end=True)
        el0 = next(data_provider)
        el1 = next(data_provider)

        regex = re.compile("(\d+)@company.com")
        logging.info(regex.findall(el0.email))
        id0 = self.extract_id(el0, regex)
        id1 = self.extract_id(el1, regex)
        logging.info(json.dumps(el0))
        logging.info(json.dumps(el1))
        logging.info(id0)
        logging.info(id1)
        assert (id0 + 1) != id1
        logging.info("passed test_random_strategy")
        self.reset_data()
        pass

    def test_sequential_strategy(self): 
        data_provider = SequentialDataProviderStrategy(self.data, return_as_dict=False, loop_on_end=True)
        el0 = next(data_provider)
        el1 = next(data_provider)
        regex = re.compile("(\d+)@company.com")
        logging.info(el0)
        logging.info(el1)
        id0 = self.extract_id(el0, regex)
        id1 = self.extract_id(el1, regex)
        assert id0 + 1 == id1
        for i in range(2000):
            assert next(data_provider) is not None
        logging.info("passed test_sequential_strategy")
        self.reset_data()

        data_provider = SequentialDataProviderStrategy(self.data, return_as_dict=False, loop_on_end=False)
        i = 0
        for el in data_provider:
            i += 1
            assert i <= 2000
        pass

    def test_unique_sequential_strategy(self): 
        data_provider = UniqueSequentialDataProviderStrategy(self.data, return_as_dict=False, loop_on_end=True)
        el0 = next(data_provider)
        el1 = next(data_provider)
        logging.info(el0)
        logging.info(el1)
        regex = re.compile("(\d+)@company.com")
        id0 = self.extract_id(el0, regex)
        id1 = self.extract_id(el1, regex)
        assert id0 != id1
        for i in data_provider:
            assert id0 != i
        self.reset_data()
        pass

    def extract_id(self, el, regex):
        return int(regex.findall(el.email)[0])


if __name__ == "__main__":
    unittest.main()