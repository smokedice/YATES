class Group():
    
    def __init__(self, name='', desc='', tests=None):
        if not tests: tests = []
        if not isinstance(tests, list):
            tests = [tests]
        self.name = name
        self.desc = desc
        self.tests = tests
        
    def addTest(self, test):
        self.tests.append(test)
        
    def removeTest(self, test):
        self.tests.remove(test)
    
    def __str__(self):
        ret = "Group Name: %s\nGroup Description: %s\n" \
                             % (self.name, self.desc)
        for test in self.tests:
            ret = ret + "   %s" % str(test)
            
        return ret