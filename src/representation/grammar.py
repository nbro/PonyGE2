from utilities.helper_methods import python_filter
from algorithm.parameters import params
from operators import initialisers
from re import search, findall
from itertools import groupby


class grammar(object):
    """ Context Free Grammar """
    NT = "NT"  # Non Terminal
    T = "T"  # Terminal

    def __init__(self, file_name):
        if file_name.endswith("pybnf"):
            self.python_mode = True
        else:
            self.python_mode = False
        self.rules = {}
        self.permutations = {}
        self.non_terminals, self.terminals = {}, []
        self.start_rule = None
        self.codon_size = params['CODON_SIZE']
        self.read_bnf_file(file_name)
        self.check_depths()
        self.check_permutations()
        self.min_ramp = initialisers.get_min_ramp_depth(self)
        self.crossover_NTs = [i for i in self.non_terminals if self.non_terminals[i]['b_factor'] > 1]

    def read_bnf_file(self, file_name):
        """Read a grammar file in BNF format"""
        # <.+?> Non greedy match of anything between brackets
        non_terminal_pattern = "(<.+?>)"
        rule_separator = "::="
        production_separator = "|"

        # Read the grammar file
        for line in open(file_name, 'r'):
            if not line.startswith("#") and line.strip() != "":
                # Split rules. Everything must be on one line
                if line.find(rule_separator):
                    lhs, productions = line.split(rule_separator)
                    lhs = lhs.strip()
                    if not search(non_terminal_pattern, lhs):
                        raise ValueError("lhs is not a NT:", lhs)
                    self.non_terminals[str(lhs)] = {"id":lhs, "min_steps":9999999999999, "expanded":False, 'recursive':True, 'permutations':None, 'b_factor':0}
                    if self.start_rule == None:
                        self.start_rule = (lhs, self.NT)
                    # Find terminals
                    tmp_productions = []
                    for production in [production.strip()
                                       for production in
                                       productions.split(production_separator)]:
                        tmp_production = []
                        if not search(non_terminal_pattern, production):
                            self.terminals.append(production)
                            tmp_production.append([production, self.T, 0, False])
                        else:
                            # Match non terminal or terminal pattern
                            # TODO does this handle quoted NT symbols?
                            for value in findall("<.+?>|[^<>]*", production):
                                if value != '':
                                    if not search(non_terminal_pattern,
                                                     value):
                                        symbol = [value, self.T, 0, False]
                                        self.terminals.append(value)
                                    else:
                                        symbol = [value, self.NT]
                                    tmp_production.append(symbol)
                        tmp_productions.append(tmp_production)
                    # Create a rule
                    if not lhs in self.rules:
                        self.rules[lhs] = tmp_productions
                    else:
                        raise ValueError("lhs should be unique", lhs)
                else:
                    raise ValueError("Each rule must be on one line")

    def check_depths(self):
        """ Run through a grammar and find out the minimum distance from each
            NT to the nearest T. Useful for initialisation methods where we
            need to know how far away we are from fully expanding a tree
            relative to where we are in the tree and what the depth limit is.

            For each NT in self.non_terminals we have:
             - 'id':        the NT itself
             - 'min_steps': its minimum distance to the nearest T (i.e. its
                            minimum distance to full expansion
             - 'expanded':  a boolean indicator for whether or not it is fully
                            expanded
             - 'b_factor':  the branching factor of the NT (now many choices
                            does  the rule have)
             - 'recursive': is the NT recursive
             - 'permutations':  the number of possible permutations and
                                combinations that this NT can produce
                                (excluding recursive rules)
        """

        for i in range(len(self.non_terminals)):
            for NT in self.non_terminals:
                vals = self.non_terminals[NT]
                vals['b_factor'] = len(self.rules[NT])
                if not vals['expanded']:
                    choices = self.rules[NT]
                    terms = 0
                    for choice in choices:
                        if not (all([sym[1] == self.T for sym in choice]) == False):
                            terms += 1
                    if terms:
                        # this NT can then map directly to a T
                        vals['min_steps'] = 1
                        vals['expanded'] = True
                    else:
                        # There are NTs remaining in the production choices
                        for choice in choices:
                            NT_s = [sym for sym in choice if sym[1] == self.NT]
                            NT_choices = list(NT_s for NT_s,_ in groupby(NT_s))
                            if len(NT_choices) > 1:
                                if all([self.non_terminals[item[0]]['expanded'] for item in NT_choices]) == True:
                                    if vals['expanded'] and (vals['min_steps'] > max([self.non_terminals[item[0]]['min_steps'] for item in NT_choices]) + 1):
                                        vals['min_steps'] = max([self.non_terminals[item[0]]['min_steps'] for item in NT_choices]) + 1
                                    elif not vals['expanded']:
                                        vals['expanded'] = True
                                        vals['min_steps'] = max([self.non_terminals[item[0]]['min_steps'] for item in NT_choices]) + 1
                            else:
                                child = self.non_terminals[NT_choices[0][0]]
                                if child['expanded']:
                                    if vals['expanded'] and (vals['min_steps'] > child['min_steps'] + 1):
                                        vals['min_steps'] = child['min_steps'] + 1
                                    else:
                                        vals['expanded'] = True
                                        vals['min_steps'] = child['min_steps'] + 1

        for i in range(len(self.non_terminals)):
            for NT in self.non_terminals:
                vals = self.non_terminals[NT]
                if vals['recursive']:
                    choices = self.rules[NT]
                    terms = 0
                    nonrecurs = 0
                    for choice in choices:
                        if not (all([sym[1] == self.T for sym in choice]) == False):
                            # This production choice is all terminals
                            terms += 1
                        temp = [bit for bit in choice if bit[1] == 'NT']
                        orary = 0
                        for bit in temp:
                            if self.non_terminals[bit[0]]['recursive'] == False:
                                orary += 1
                        if (orary == len(temp)) and temp:
                            # then all NTs in this production choice are not
                            # recursive
                            nonrecurs += 1
                    if terms == len(choices):
                        # this means all the production choices for this NT are
                        # terminals, it most definitely isn't recursive.
                        vals['recursive'] = False
                    elif (terms + nonrecurs) == len(choices):
                        # this means all the production choices for this NT are
                        # not recursive; it isn't recursive by proxy.
                        vals['recursive'] = False

        if self.start_rule[0] in self.non_terminals:
            self.min_path = self.non_terminals[self.start_rule[0]]['min_steps']
        else:
            print ("Error: start rule not a non-terminal")
            quit()
        self.max_arity = 0
        for NT in self.non_terminals:
            if self.non_terminals[NT]['min_steps'] > self.max_arity:
                self.max_arity = self.non_terminals[NT]['min_steps']
        for rule in self.rules:
            for prod in self.rules[rule]:
                for sym in [i for i in prod if i[1] == self.NT]:
                    sym.append(self.non_terminals[sym[0]]['min_steps'])
        for rule in self.rules:
            for prod in self.rules[rule]:
                for sym in [i for i in prod if i[1] == self.NT]:
                    sym.append(self.non_terminals[sym[0]]['recursive'])

    def check_permutations(self, ramps=5):
        """ Calculates how many possible derivation tree combinations can be
            created from the given grammar at a specified depth. Only returns
            possible combinations at the specific given depth (if there are no
            possible permutations for a given depth, will return 0).
        """

        perms_list = []
        if self.max_arity > self.min_path:
            for i in range(max((self.max_arity+1 - self.min_path), ramps)):
                x = self.check_all_permutations(i + self.min_path)
                perms_list.append(x)
                if i > 0:
                    perms_list[i] -= sum(perms_list[:i])
                    self.permutations[i + self.min_path] -= sum(perms_list[:i])
        else:
            for i in range(ramps):
                x = self.check_all_permutations(i + self.min_path)
                perms_list.append(x)
                if i > 0:
                    perms_list[i] -= sum(perms_list[:i])
                    self.permutations[i + self.min_path] -= sum(perms_list[:i])

    def check_all_permutations(self, depth):
        """ Calculates how many possible derivation tree combinations can be
            created from the given grammar at a specified depth. Returns all
            possible combinations at the specific given depth including those
            depths below the given depth.
        """

        if depth < self.min_path:
            # There is a bug somewhere that is looking for a tree smaller than
            # any we can create
            print ("Error: cannot check permutations for tree smaller than the minimum size")
            quit()
        if depth in self.permutations.keys():
            return self.permutations[depth]
        else:
            pos = 0
            terminalSymbols = self.terminals
            depthPerSymbolTrees = {}
            productions = []
            for NT in self.non_terminals:
                a = self.non_terminals[NT]
                for rule in self.rules[a['id']]:
                    if any([prod[1] is self.NT for prod in rule]):
                        productions.append(rule)

            startSymbols = self.rules[self.start_rule[0]]

            for prod in productions:
                depthPerSymbolTrees[str(prod)] = {}

            for i in range(2, depth+1):
                # Find all the possible permutations from depth of min_path up
                # to a specified depth
                for ntSymbol in productions:
                    symPos = 1
                    for j in ntSymbol:
                        symbolArityPos = 0
                        if j[1] is self.NT:
                            for child in self.rules[j[0]]:
                                if len(child) == 1 and child[0][0] in self.terminals:
                                    symbolArityPos += 1
                                else:
                                    if (i - 1) in depthPerSymbolTrees[str(child)].keys():
                                        symbolArityPos += depthPerSymbolTrees[str(child)][i - 1]
                            symPos *= symbolArityPos
                    depthPerSymbolTrees[str(ntSymbol)][i] = symPos

            for sy in startSymbols:
                if str(sy) in depthPerSymbolTrees:
                    pos += depthPerSymbolTrees[str(sy)][depth] if depth in depthPerSymbolTrees[str(sy)] else 0
                else:
                    pos += 1
            self.permutations[depth] = pos
            return pos

    def __str__(self):
        return "%s %s %s %s" % (self.terminals, self.non_terminals,
                                self.rules, self.start_rule)

    def generate(self, _input, max_wraps=0):
        """ The genotype to phenotype mappping process. Map input via rules to
        output. Returns output and used_input. """
        #TODO check tree depths to see if correct
        used_input, current_depth, current_max_depth, nodes = 0, 0, 0, 1
        wraps, output, production_choices = -1, [], []
        unexpanded_symbols = [(self.start_rule, 0)]

        while (wraps < max_wraps) and \
                (len(unexpanded_symbols) > 0) and\
                (current_max_depth <= params['MAX_TREE_DEPTH']):
            # Wrap
            if used_input % len(_input) == 0 and \
                    used_input > 0 and \
                    any([i[0][1] == "NT" for i in unexpanded_symbols]):
                wraps += 1

            # Expand a production
            current_item = unexpanded_symbols.pop(0)
            current_symbol, current_depth = current_item[0], current_item[1]
            if current_max_depth < current_depth:
                current_max_depth = current_depth
            # Set output if it is a terminal
            if current_symbol[1] != self.NT:
                output.append(current_symbol[0])

            else:
                production_choices = self.rules[current_symbol[0]]
                # Select a production
                current_production = _input[used_input % len(_input)] % len(production_choices)
                # Use an input if there was more then 1 choice
                if len(production_choices) > 1:
                    used_input += 1
                # Derviation order is left to right(depth-first)
                children = []
                for prod in production_choices[current_production]:
                    children.append([prod, current_depth+1])

                NT_kids = [child for child in children if child[0][1] == "NT"]
                if any(NT_kids):
                    nodes += len(NT_kids)
                else:
                    nodes += 1
                unexpanded_symbols = children + unexpanded_symbols

        if len(unexpanded_symbols) > 0:
            # Not completly expanded, invalid solution.
            return output, _input, None, nodes, True, current_max_depth+1, \
                   used_input

        output = "".join(output)
        if self.python_mode:
            output = python_filter(output)
        return output, _input, None, nodes, False, current_max_depth+1,\
               used_input