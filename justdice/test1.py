class X(object):
    def __init__(self, kwargs):
        #print self.__dict__
        self.__dict__.update(**kwargs)
        #setattr(self, name, val)

    def run(self):
        print "run!"


x = X({'run': 2})
print x.run
