from itertools import chain

class Source():
    def __init__(self, location = '', groups = []):
        if not isinstance(groups, list):
            groups = [groups]
        self.location = location 
        self.groups = groups

    def getTests(self):
        """ Retrieve all tests """
        return list(chain(*[ g.tests for g in self.groups ]))
