def processDocStrings(doc):
    docstrings = {'summary' : ''} 
    oldKey = 'summary' 

    for line in doc.splitlines():
        line = line.strip()

        if len(line) == 0: continue
        elif not line[0] == '@' or not line.find(':') >= 2: 
            docstrings[oldKey] += '\n%s' % line.strip()
            continue

        k, v = line.split(':', 1)
        k = k[1:].strip()
        v = v.strip()
        oldKey = k

        if k not in docstrings.keys(): docstrings[k] = v 
        else: docstrings[k] = docstrings[k].join(v.strip())

    return docstrings


if __name__ == '__main__':
    x = """
    Summary blah value something \
        blah value something car
    @result: resultingness
    @value: key
    @ weird : something else
    """
    import pdb
    pdb.set_trace()

    t = processDocStrings(x)
    print t
