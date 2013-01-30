import sys, os
from xml.dom.minidom import parse, Element

if len(sys.argv) != 2:
    print 'Requires a single XSD file'
    sys.exit(-1)

if not os.path.exists(sys.argv[1]):
    print '%s does not exist'
    sys.exit(-2)

xsd_doc = parse(sys.argv[1])
root = xsd_doc.childNodes[0]

def attr_value(key, attributes, default = None):
    if not attributes.has_key(key): 
        return default
    return attributes.getNamedItem(key).value

def gather_nodes(node, _all_nodes = None, _layer = 0):
    if not _all_nodes: _all_nodes = {}
    if not isinstance(node, Element): return None, _all_nodes
    node_doc = None

    child_nodes = []
    for cn in node.childNodes:
        cns, _all_nodes = gather_nodes(cn, _all_nodes, _layer + 1)
        if not cns and cn.nodeName.endswith('annotation'):
            assert node_doc == None
            node_doc = cn.childNodes[1].childNodes[0].nodeValue
            node_doc = ' '.join([ x.strip() for x in node_doc.strip().splitlines()])
        if not cns: continue
        child_nodes += cns

    ref = attr_value('ref', node.attributes, '')
    name = ref[:]

    if name == '': name = attr_value('name', node.attributes)
    if not name: return child_nodes, _all_nodes

    card_min = attr_value('minOccurs', node.attributes, 'undefined')
    card_max = attr_value('maxOccurs', node.attributes, 'undefined')
    return_node = (name, node_doc or '', card_min, card_max, child_nodes)

    if len(ref) == 0 and _layer == 1:
        assert name not in _all_nodes.keys(), name
        _all_nodes[name] = return_node
    return [return_node], _all_nodes

def print_nodes(nodes, all_nodes, tab = ' '):
    for node in nodes:
        name, doc, card_min, card_max, child_nodes = node

        if ':' in node[0]:
            name = str(node[0].split(':', 1)[1])
            node = all_nodes[name]

        name, doc, n_card_min, n_card_max, child_nodes = node
        if card_min == 'undefined': card_min = n_card_min
        if card_max == 'undefined': card_max = n_card_max

        print '<div class="config">'
        print '<h4>%s</h4>' % name
        print '<div class="config-text">'
        print 'Cardinality: %s..%s<br />' %(card_min, card_max)
        if doc != '':
            print 'Description:<br />'
            print '<p>', doc, '</p>'

        if len(child_nodes) > 0:
            print 'Children:'
            print_nodes(child_nodes, all_nodes, tab + '    ')
        print '</div></div>'

nodes, all_nodes = gather_nodes(root)
print '<html><head></head><body>'
print_nodes(nodes[:1], all_nodes)
print '</body></html>'
