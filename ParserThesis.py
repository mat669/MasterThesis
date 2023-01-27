import uunet.multinet as ml
import numpy as np

def parse_language_file(language_file):
    print(f'Parsing MLN language file {language_file}')
    language = {
        'states': [],
        'parameters': [],
        'initial conditions': [],
        'rules': [],
        'views': [],
        'simOptions': [],
        'reachability property': [],
        'escape property':[],
        'somewhere property': [],
        'everywhere property': [],
        'surround property': []
    }
    
    language_file = open(language_file, 'r').readlines()
    
    saving_lines = False
    key = ''
    for line in language_file:
        if 'begin' in line:
            saving_lines = True
            l = line.split()[1:]
            if len(l) > 1:
                l = ' '.join(l)
            else:
                l = l[0]
            key = l
        elif 'end' in line:
            saving_lines = False

        if saving_lines and 'begin' not in line:
            language[key].append(line.strip('\n'))
            
    return language
    

def parse_mln(mln_filename):

  print(f'Parsing network configuration file {mln_filename}')
  net = ml.read(mln_filename)

  ### Number of actors
  actors = list(map(lambda x: str(x),sorted(list(map(lambda x:int(x), ml.actors(net))))))
  # N_actors = max(list(map(int, actors)))
  N_actors = len(actors)


  ### Number of layers
  layers = sorted(ml.layers(net))
  # N_layers = max(list(map(int, layers)))
  N_layers = len(layers)


  #### Then we extract all the edges we need from the MLN
  #### (here i check if they undirected and take them both, maybe it is best to do this check in
  #### when parsing the rules)

  edges = ml.edges(net)
  couples = []
  for i in range(len(edges['from_actor'])):
    new_coup = ()
    new_coup += (edges['from_actor'][i],)
    new_coup += (edges['from_layer'][i],)
    new_coup += (edges['to_actor'][i],)
    new_coup += (edges['to_layer'][i],)
    couples.append(new_coup)
  couples = sorted(couples, key = lambda x:x[1])
  edges['from_actor'] = []
  edges['from_layer'] = []
  edges['to_actor'] = []
  edges['to_layer'] = []
  for couple in couples:
    edges['from_actor'].append(couple[0])
    edges['from_layer'].append(couple[1])
    edges['to_actor'].append(couple[2])
    edges['to_layer'].append(couple[3])


  list_split_edges = [] 

  for layer in layers: 
    list_collecting_edges = [] 
    idx_list = [i for i,j in enumerate(edges['from_layer']) if j == layer]
    for i in idx_list : 
        list_collecting_edges.append((edges['from_actor'][i] , edges['to_actor'][i]) )
        if edges['dir'][i] == False: 
            list_collecting_edges.append( (edges['to_actor'][i] , edges['from_actor'][i]) )

    list_split_edges.append(list_collecting_edges)


  mln_data = {
      'actors': (actors, N_actors),
      'layers': (layers, N_layers),
      'edges': (edges, list_split_edges)
              }
    
  return mln_data


def kappa_parse_signatures(mln_data, language):
    signatures = []
    
    states = '{' + ', '.join(language['states']) + '}'

    for i in language['initial conditions']:
        actor,state = i.split('=')
        actor= actor.strip()
        sites = []
        for j,layer in zip(mln_data['layers'][0],mln_data['edges'][1]):
            for edge in layer:
                if edge[0] == str(actor):
                    sites.append(f'l{j}v{edge[1]}')
        sites = ', '.join(sites)
                                 
        kappa_signature = f'%agent: V{str(actor)}(state{states}, {sites})'
        signatures.append(kappa_signature)
        
        
    signatures = '\n'.join(signatures)

    return signatures


def kappa_parse_variables(language):
    variables = []
    
    for param in language['parameters']:
        var_name, var_value = param.split('=')
        var = f"%var: {var_name.strip()} {var_value.strip()}"
        variables.append(var)
    variables = '\n'.join(variables)
    
    return variables

def kappa_parse_observables(mln_data, language):
    observables = []
    for view in language['views']:
        components = []
        for i in language['initial conditions']:
          actor,state = i.split('=')
          actor= actor.strip()
          state = state.strip()
          components.append(f'|V{actor}(state{{{view}}})|')
        obs = f"%obs: '{view}' " + ' + '.join(components)
        observables.append(obs)
    observables = '\n'.join(observables)
    return observables


def kappa_parse_observables_first_part(mln_data, language):
    observables = []
    
    for view in language['views']:
        components = []
        for i, actor in enumerate(range(1,len(language['initial conditions'])+1)):
            components.append(f'|V{i+1}(state{{{view}}})|')
        obs = f"%obs: '{view}' " + ' + '.join(components)
        observables.append(obs)
    for i, actor in enumerate(range(1,len(language['initial conditions'])+1)):
      for view in language['views']:
          obs = f"%obs: 'V{i+1}{view}' |V{i+1}(state{{{view}}})|"
          observables.append(obs)
    observables = '\n'.join(observables)
    return observables

  
def kappa_parse_initial_conditions(mln_data, language):
    n = ''
    for line in language['simOptions']:
        option, value = line.split('=')
        if option.strip() == 'n':
            n = value.strip()
            break
    i_c = [
          f'%init: {n} (']

    initial_states = [x.split('=') for x in language['initial conditions']]
    for el in initial_states:
      el[0] = el[0].strip()
      el[1] = el[1].strip()
    site_labels = {}
    for j, layer in zip(mln_data['layers'][0],mln_data['edges'][1]):
        for edge in layer:
          if edge[0] <= edge[1]:
            site_label = f'{j}{edge[0]}{edge[1]}'
            if edge[0] not in site_labels:
                site_labels[edge[0]] = [f'l{j}v{edge[1]}[{site_label}]']
            else:
                site_labels[edge[0]].append(f'l{j}v{edge[1]}[{site_label}]')
          else:
            site_label = f'{j}{edge[1]}{edge[0]}'
            if edge[0] not in site_labels:
                site_labels[edge[0]] = [f'l{j}v{edge[1]}[{site_label}]']
            else:
                site_labels[edge[0]].append(f'l{j}v{edge[1]}[{site_label}]')

    for state in initial_states:
      condition = f'V{int(state[0])}(state{{{state[1]}}}'
      if state[0] in site_labels:
        for site in site_labels[state[0]]:
          condition +=  f",{site}"
      else:
        condition = condition + ','
      i_c.append(condition + '),')
    i_c[-1] = i_c[-1][:-1]
    i_c.append(')')
    i_c = '\n'.join(i_c)
    return i_c


def kappa_parse_rules(mln_data, language):
    kappa_rules = []
    
    rules = [x.split('@') for x in language['rules']]
    rules_organised = []
    for ruleset in rules:
        rules_organised.append({'rule': ruleset[0].strip(), 'rate': ruleset[1].strip()})
      
    rule_counter = list(range(len(rules_organised)))
    for ruleset in rules_organised:
        if '=' not in ruleset['rule']:
            # parse rules not dependant on layers
            rule_states = [state.strip() for state in ruleset['rule'].split('->')]
            for i in mln_data['actors'][0]:
                kappa_rule = f"V{i}(state{{{rule_states[0]}}}) -> V{i}(state{{{rule_states[1]}}}) @ {ruleset['rate']}"
                kappa_rules.append(f"'rule{rule_counter[rules_organised.index(ruleset)]}_{i}'" + kappa_rule)
        else:
            # parse intra-layer rules
            # requires rules in both directions
            rule_sides = [state.strip() for state in ruleset['rule'].split('->')]
            layer = rule_sides[0][rule_sides[0].index('=')+1].strip()

            states = [[x[0].strip(), x[1].strip()] for x in [rule_side.split(f'={layer}') for rule_side in rule_sides]]
            for el,edge in enumerate(mln_data['edges'][1][int(layer)-1]):
                v1, v2 = edge[0], edge[1]
                site_label = f'{layer}{v1}{v2}'
                kappa_rule = (f'V{v1}(state{{{states[0][0]}}}, l{layer}v{v2}[{site_label}]), V{v2}(state{{{states[0][1]}}}, l{layer}v{v1}[{site_label}]) -> '
                    f'V{v1}(state{{{states[1][0]}}}, l{layer}v{v2}[{site_label}]), V{v2}(state{{{states[1][1]}}}, l{layer}v{v1}[{site_label}]) @ '
                    f"{ruleset['rate']}")

                kappa_rules.append(f"'rule{rule_counter[rules_organised.index(ruleset)]}_{el}'" + kappa_rule)


    kappa_rules = '\n'.join(kappa_rules)

    return kappa_rules

def kappa_intervention_based(numb_events):
  return f'%mod: [E] [mod] {numb_events} = 0 do $PLOTENTRY ; repeat [true]'


def kappa_parse_reachability(mln_data, language):
  specifications = []

  cond1, stopper_and_cond2 = language['reachability property'][0].split('R')

  first_condition_specification = '' 
  cond1_components = cond1.strip(" ()").split(',')
  if '*' in cond1_components[0]: #node level specification
    if len(cond1_components[0].split('*')) == 2:
      agent,state = cond1_components[0].split('*')
      agent = agent.strip()
      state = state.strip()
      first_condition_specification += f"|V{agent}(state{{{state}}})|"
    else:
      multiple_nodes = cond1_components[0].split('&')
      for item in multiple_nodes[:-1]:
        node,state = item.split('*')
        node = node.strip()
        state = state.strip()
        first_condition_specification += f"|V{node}(state{{{state}}})| + "
      last_node, last_state = multiple_nodes[-1].split('*')
      last_node = last_node.strip()
      last_state = last_state.strip()
      first_condition_specification += f"|V{last_node}(state{{{last_state}}})|"
  else: #it is a state specififcation
    nodes = []
    for node in mln_data['actors'][0]:
      nodes.append(f"|V{node}(state{{{cond1_components[0]}}})|") 
    for node_count in nodes[:-1]:
      first_condition_specification += node_count + ' + '
    first_condition_specification += nodes[-1]
  operator1 = cond1_components[1].strip()
  threshold1 = cond1_components[2].strip()

  stopper, cond2 = stopper_and_cond2.strip().split("&&")
  stopper_type, stopper_value = stopper.split('=')
  stopper_type_kappy = {'t':'T','e':'E'}
  cond2_components = cond2.strip(" ()").split(',')
  second_condition_specification = '' 
  if '*' in cond2_components[0]: #node level specification
    if len(cond2_components[0].split('*')) == 2:
      agent,state = cond2_components[0].split('*')
      agent = agent.strip()
      state = state.strip()
      second_condition_specification += f"|V{agent}(state{{{state}}})|"
    else:
      multiple_nodes = cond2_components[0].split('&')
      for item in multiple_nodes[:-1]:
        node,state = item.split('*')
        node = node.strip()
        state = state.strip()
        second_condition_specification += f"|V{node}(state{{{state}}})| + "
      last_node, last_state = multiple_nodes[-1].split('*')
      last_node = last_node.strip()
      last_state = last_state.strip()
      second_condition_specification += f"|V{last_node}(state{{{last_state}}})|" 
  else: #it is a state specififcation
    nodes = []
    for node in mln_data['actors'][0]:
      nodes.append(f"|V{node}(state{{{cond2_components[0]}}})|")
    for node_count in nodes[:-1]:
      second_condition_specification += node_count + ' + '
    second_condition_specification += nodes[-1]
  operator2 = cond2_components[1].strip()
  threshold2 = cond2_components[2].strip()

  reach_var = 'reachability_property_satisfaction'
  var1 = 'first_condition_reachability'
  var2 = 'second_condition_reachability'

  #### variables specification
  specifications.append(f"%var: '{var1}' {first_condition_specification}")
  specifications.append(f"%var: {var2} {second_condition_specification}")
  specifications.append(f"%var: '{reach_var}' 0")
  specifications.append(f"%var: 'first_condition_satisfaction' 1")

    ### observables specification
  specifications.append(f"%obs: 'property_reachability' '{reach_var}'")
  specifications.append(f"%obs: 'content_condition1' '{var1}'")
  specifications.append(f"%obs: 'content_condition2' '{var2}'")

  ### property checking --> relevance of the order: if the guards are simultaneosuly satisfied, first mod declared is the first applied
  specifications.append(f"%mod: [{stopper_type_kappy[stopper_type]}] < {stopper_value} && [not] ('{var1}' {operator1} {threshold1}) do $UPDATE 'first_condition_satisfaction' 0;")
  specifications.append(f"%mod: [{stopper_type_kappy[stopper_type]}] < {stopper_value} && 'first_condition_satisfaction'=1 && '{var2}' {operator2} {threshold2} do $UPDATE '{reach_var}' 1;")

  

  specifications = '\n'.join(specifications)

  return specifications

def kappa_parse_escape(mln_data, language):
  specifications = []

  empty, stopper_and_cond2 =language['escape property'][0].split('E')

  stopper, cond2 = stopper_and_cond2.strip().split("&&")
  stopper_type, stopper_value = stopper.split('=')
  stopper_type_kappy = {'t':'T','e':'E'}
  cond2_components = cond2.strip(" ()").split(',')
  second_condition_specification = '' 
  if '*' in cond2_components[0]: #node level specification
    if len(cond2_components[0].split('*')) == 2:
      agent,state = cond2_components[0].split('*')
      agent = agent.strip()
      state = state.strip()
      second_condition_specification += f"|V{agent}(state{{{state}}})|"
    else:
      multiple_nodes = cond2_components[0].split('&')
      for item in multiple_nodes[:-1]:
        node,state = item.split('*')
        node = node.strip()
        state = state.strip()
        second_condition_specification += f"|V{node}(state{{{state}}})| + "
      last_node, last_state = multiple_nodes[-1].split('*')
      last_node = last_node.strip()
      last_state = last_state.strip()
      second_condition_specification += f"|V{last_node}(state{{{last_state}}})|" 
  else: #it is a state specififcation
    nodes = []
    for node in mln_data['actors'][0]:
      nodes.append(f"|V{node}(state{{{cond2_components[0]}}})|")
    for node_count in nodes[:-1]:
      second_condition_specification += node_count + ' + '
    second_condition_specification += nodes[-1]
  op = cond2_components[1].strip()
  value = cond2_components[2].strip()

  escape_var = 'escape_property_satisfaction'
  var2 = 'condition_escape'

  #### variables specification
  specifications.append(f"%var: {var2} {second_condition_specification}")
  specifications.append(f"%var: '{escape_var}' 1")


    ### observables specification
  specifications.append(f"%obs: 'property_escape' '{escape_var}'")
  specifications.append(f"%obs: 'content_escape' '{var2}'")

  ### property checking : remember that, differnetly from reachability, in escape the stopper value is a lower bound
  specifications.append(f"%mod: [{stopper_type_kappy[stopper_type]}] < {stopper_value} &&  [not]('{var2}' {op} {value}) do $UPDATE '{escape_var}' 0;")

  specifications = '\n'.join(specifications)

  return specifications

def kappa_parse_somewhere(mln_data, language):

  specifications = []

  empty, stopper_and_cond2 =language['somewhere property'][0].split('SOMEWHERE')

  stopper, cond2 = stopper_and_cond2.strip().split("&&")
  stopper_type, stopper_value = stopper.split('=')
  stopper_type_kappy = {'t':'T','e':'E'}
  cond2_components = cond2.strip(" ()").split(',')
  second_condition_specification = '' 
  if '*' in cond2_components[0]: #node level specification
    if len(cond2_components[0].split('*')) == 2:
      agent,state = cond2_components[0].split('*')
      agent = agent.strip()
      state = state.strip()
      second_condition_specification += f"|V{agent}(state{{{state}}})|"
    else:
      multiple_nodes = cond2_components[0].split('&')
      for item in multiple_nodes[:-1]:
        node,state = item.split('*')
        node = node.strip()
        state = state.strip()
        second_condition_specification += f"|V{node}(state{{{state}}})| + "
      last_node, last_state = multiple_nodes[-1].split('*')
      last_node = last_node.strip()
      last_state = last_state.strip()
      second_condition_specification += f"|V{last_node}(state{{{last_state}}})|" 
  else: #it is a state specififcation
    nodes = []
    for node in mln_data['actors'][0]:
      nodes.append(f"|V{node}(state{{{cond2_components[0]}}})|")
    for node_count in nodes[:-1]:
      second_condition_specification += node_count + ' + '
    second_condition_specification += nodes[-1]
  op = cond2_components[1].strip()
  value = cond2_components[2].strip()

  somewhere_var = 'somewhere_property_satisfaction'
  var2 = 'condition_somewhere'

  #### variables specification
  specifications.append(f"%var: {var2} {second_condition_specification}")
  specifications.append(f"%var: '{somewhere_var}' 0")


    ### observables specification
  specifications.append(f"%obs: 'property_somewhere' '{somewhere_var}'")
  specifications.append(f"%obs: 'content_somewhere' '{var2}'")

  ### property checking
  specifications.append(f"%mod: [{stopper_type_kappy[stopper_type]}] < {stopper_value} && '{var2}' {op} {value} do $UPDATE '{somewhere_var}' 1;")

  specifications = '\n'.join(specifications)

  return specifications

def kappa_parse_everywhere(mln_data, language):

  specifications = []

  empty, stopper_and_cond2 =language['everywhere property'][0].split('EVERYWHERE')

  stopper, cond2 = stopper_and_cond2.strip().split("&&")
  stopper_type, stopper_value = stopper.split('=')
  stopper_type_kappy = {'t':'T','e':'E'}
  cond2_components = cond2.strip(" ()").split(',')
  second_condition_specification = '' 
  if '*' in cond2_components[0]: #node level specification
    if len(cond2_components[0].split('*')) == 2:
      agent,state = cond2_components[0].split('*')
      agent = agent.strip()
      state = state.strip()
      second_condition_specification += f"|V{agent}(state{{{state}}})|"
    else:
      multiple_nodes = cond2_components[0].split('&')
      for item in multiple_nodes[:-1]:
        node,state = item.split('*')
        node = node.strip()
        state = state.strip()
        second_condition_specification += f"|V{node}(state{{{state}}})| + "
      last_node, last_state = multiple_nodes[-1].split('*')
      last_node = last_node.strip()
      last_state = last_state.strip()
      second_condition_specification += f"|V{last_node}(state{{{last_state}}})|" 
  else: #it is a state specififcation
    nodes = []
    for node in mln_data['actors'][0]:
      nodes.append(f"|V{node}(state{{{cond2_components[0]}}})|")
    for node_count in nodes[:-1]:
      second_condition_specification += node_count + ' + '
    second_condition_specification += nodes[-1]
  op = cond2_components[1].strip()
  value = cond2_components[2].strip()

  everywhere_var = 'everywhere_property_satisfaction'
  var2 = 'condition_everywhere'

  #### variables specification
  specifications.append(f"%var: {var2} {second_condition_specification}")
  specifications.append(f"%var: '{everywhere_var}' 1")


    ### observables specification
  specifications.append(f"%obs: 'property_everywhere' '{everywhere_var}'")
  specifications.append(f"%obs: 'content_everywhere' '{var2}'")

  ### property checking
  specifications.append(f"%mod: [{stopper_type_kappy[stopper_type]}] < {stopper_value} && [not] ('{var2}' {op} {value}) do $UPDATE '{everywhere_var}' 0;")

  specifications = '\n'.join(specifications)

  return specifications



def kappa_parse_surround(mln_data, language,network_filename):
  specifications = []

  cond1, stopper_and_cond2 = language['surround property'][0].split('SURROUND')

  cond1, stopper_and_cond2 = language['surround property'][0].split('SURROUND')

  first_condition_specification = '' 
  agents = []
  cond1_components = cond1.strip(" ()").split(',')
  if '*' in cond1_components[0]: #node level specification
    if len(cond1_components[0].split('*')) == 2:
      agent,state = cond1_components[0].split('*')
      agent = agent.strip()
      agents.append(str(agent[-1]))
      state = state.strip()
      first_condition_specification += f"|V{agent}(state{{{state}}})|"
    else:
      multiple_nodes = cond1_components[0].split('&')
      for item in multiple_nodes[:-1]:
        node,state = item.split('*')
        node = node.strip()
        agents.append(str(node[-1]))
        state = state.strip()
        first_condition_specification += f"|V{node}(state{{{state}}})| + "
      last_node, last_state = multiple_nodes[-1].split('*')
      last_node = last_node.strip()
      agents.append(str(last_node[-1]))
      last_state = last_state.strip()
      first_condition_specification += f"|V{last_node}(state{{{last_state}}})|"
  else: #it is a state specififcation
    nodes = []
    for node in mln_data['actors'][0]:
      agents.append(node)
      nodes.append(f"|V{node}(state{{{cond1_components[0]}}})|") 
    for node_count in nodes[:-1]:
      first_condition_specification += node_count + ' + '
    first_condition_specification += nodes[-1]
  operator1 = cond1_components[1].strip()
  threshold1 = cond1_components[2].strip()


  stopper, cond2 = stopper_and_cond2.strip().split("&&")
  stopper_type, stopper_value = stopper.split('=')
  stopper_type = stopper_type.strip()
  stopper_type_kappy = {'t':'T','e':'E'}
  cond2_components = cond2.strip(" ()").split(',')

  second_condition_specification = '' 

  if '*' in cond2_components[0]: #node level specification
    if len(cond2_components[0].split('*')) == 2:
      agent,state = cond2_components[0].split('*')
      agent = agent.strip()
      state = state.strip()
      second_condition_specification += f"|V{agent}(state{{{state}}})|"
    else:
      multiple_nodes = cond2_components[0].split('&')
      for item in multiple_nodes[:-1]:
        node,state = item.split('*')
        node = node.strip()
        state = state.strip()
        second_condition_specification += f"|V{node}(state{{{state}}})| + "
      last_node, last_state = multiple_nodes[-1].split('*')
      last_node = last_node.strip()
      last_state = last_state.strip()
      second_condition_specification += f"|V{last_node}(state{{{last_state}}})|" 
  else: #it is a state specififcation
    nodes = []
    for node in mln_data['actors'][0]:
      nodes.append(f"|V{node}(state{{{cond2_components[0]}}})|")
    for node_count in nodes[:-1]:
      second_condition_specification += node_count + ' + '
    second_condition_specification += nodes[-1]
  op2 = cond2_components[1].strip()
  value2 = cond2_components[2].strip()



  surround_var = 'surround_property_satisfaction'
  var1 = 'first_condition_surround'
  var2 = 'second_condition_surround'

  #### variables specification
  specifications.append(f"%var: '{var1}' {first_condition_specification}")
  specifications.append(f"%var: '{var2}' {second_condition_specification}")
  specifications.append(f"%var: '{surround_var}' 0")
  specifications.append(f"%var: 'first_condition_surround_satisfaction' 1")
  specifications.append(f"%var: 'second_condition_surround_satisfaction' 0")
  specifications.append(f"%var: 'time_of_escape_first_condition' 0")
  specifications.append(f"%var: 'time_of_reach_second_condition' 0")

  ### observables specification
  specifications.append(f"%obs: 'property_surround' '{surround_var}'")
  specifications.append(f"%obs: 'content_condition1_surround' '{var1}'")
  specifications.append(f"%obs: 'content_condition2_surround' '{var2}'")

    ### property checking
  specifications.append(f"%mod: [{stopper_type_kappy[stopper_type]}] < {stopper_value} && [not] ('{var1}' {operator1} {threshold1}) && 'first_condition_surround_satisfaction' = 1 do $UPDATE 'first_condition_surround_satisfaction' 0; $UPDATE 'time_of_escape_first_condition' [E];")
  specifications.append(f"%mod: [{stopper_type_kappy[stopper_type]}] < {stopper_value} && '{var2}' {op2} {value2} do $UPDATE 'second_condition_surround_satisfaction' 1;")
  specifications.append(f"%mod: [{stopper_type_kappy[stopper_type]}] < {stopper_value} && [not] ('{var2}' {op2} {value2}) do $UPDATE 'second_condition_surround_satisfaction' 0;")
  specifications.append(f"%mod: [E] = 'time_of_escape_first_condition' && 'time_of_escape_first_condition' > 0 && 'first_condition_surround_satisfaction' = 0 && 'second_condition_surround_satisfaction' = 1 do $UPDATE '{surround_var}' 1;")


  specifications = '\n'.join(specifications)
  return specifications


def parse_to_kappy_first_part(network_filename, language_filename, out_filename):
    mln_data = parse_mln(network_filename)
    language = parse_language_file(language_filename)
    
    kappa_model = ''
    kappa_model += kappa_parse_signatures(mln_data, language) + '\n'
    kappa_model += kappa_parse_rules(mln_data, language) + '\n'
    kappa_model += kappa_parse_variables(language) + '\n'
    kappa_model += kappa_parse_observables_first_part(mln_data, language) + '\n'
    kappa_model += kappa_parse_initial_conditions(mln_data, language) + '\n'
    if language['reachability property'] != []:
      kappa_model += kappa_parse_reachability(mln_data, language) +'\n\n'
    if language['escape property'] != []:
      kappa_model += kappa_parse_escape(mln_data, language) + '\n\n'
    if language['somewhere property'] != []:
      kappa_model += kappa_parse_somewhere(mln_data, language) + '\n\n' 
    if language['surround property'] != []:
      kappa_model += kappa_parse_surround(mln_data, language,network_filename)
    
    with open(out_filename, 'w') as f:
        f.write(kappa_model)
    print(f'Successfully exported model into Kappa: {out_filename}')


def parse_to_kappy(network_filename, language_filename, out_filename):
    mln_data = parse_mln(network_filename)
    language = parse_language_file(language_filename)
    
    kappa_model = ''
    kappa_model += kappa_parse_signatures(mln_data, language) + '\n'
    kappa_model += kappa_parse_rules(mln_data, language) + '\n'
    kappa_model += kappa_parse_variables(language) + '\n'
    kappa_model += kappa_parse_observables(mln_data, language) + '\n'
    kappa_model += kappa_parse_initial_conditions(mln_data, language) + '\n'
    if language['reachability property'] != []:
      kappa_model += kappa_parse_reachability(mln_data, language) +'\n\n'
    if language['escape property'] != []:
      kappa_model += kappa_parse_escape(mln_data, language) + '\n\n'
    if language['somewhere property'] != []:
      kappa_model += kappa_parse_somewhere(mln_data, language) + '\n\n' 
    if language['surround property'] != []:
      kappa_model += kappa_parse_surround(mln_data, language,network_filename)
    
    with open(out_filename, 'w') as f:
        f.write(kappa_model)
    print(f'Successfully exported model into Kappa: {out_filename}')


def parse_to_kappy_observed_event_first_part(network_filename, language_filename, out_filename):
    mln_data = parse_mln(network_filename)
    language = parse_language_file(language_filename)
    
    kappa_model = ''
    kappa_model += kappa_parse_signatures(mln_data, language) + '\n'
    kappa_model += kappa_parse_rules(mln_data, language) + '\n'
    kappa_model += kappa_parse_variables(language) + '\n'
    kappa_model += kappa_parse_observables_first_part(mln_data, language) + '\n'
    kappa_model += kappa_parse_initial_conditions(mln_data, language) + '\n'
    kappa_model += kappa_intervention_based(1) + '\n'
    if language['reachability property'] != []:
      kappa_model += kappa_parse_reachability(mln_data, language) +'\n\n'
    if language['escape property'] != []:
      kappa_model += kappa_parse_escape(mln_data, language) + '\n\n'
    if language['somewhere property'] != []:
      kappa_model += kappa_parse_somewhere(mln_data, language) + '\n\n' 
    if language['surround property'] != []:
      kappa_model += kappa_parse_surround(mln_data, language,network_filename)
    
    with open(out_filename, 'w') as f:
        f.write(kappa_model)
    print(f'Successfully exported model into Kappa: {out_filename}')

def parse_to_kappy_observed_event(network_filename, language_filename, out_filename):
    mln_data = parse_mln(network_filename)
    language = parse_language_file(language_filename)
    
    kappa_model = ''
    kappa_model += kappa_parse_signatures(mln_data, language) + '\n'
    kappa_model += kappa_parse_rules(mln_data, language) + '\n'
    kappa_model += kappa_parse_variables(language) + '\n'
    kappa_model += kappa_parse_observables(mln_data, language) + '\n'
    kappa_model += kappa_parse_initial_conditions(mln_data, language) + '\n'
    kappa_model += kappa_intervention_based(1) + '\n'
    if language['reachability property'] != []:
      kappa_model += kappa_parse_reachability(mln_data, language) +'\n\n'
    if language['escape property'] != []:
      kappa_model += kappa_parse_escape(mln_data, language) + '\n\n'
    if language['somewhere property'] != []:
      kappa_model += kappa_parse_somewhere(mln_data, language) + '\n\n' 
    if language['surround property'] != []:
      kappa_model += kappa_parse_surround(mln_data, language,network_filename)
    
    with open(out_filename, 'w') as f:
        f.write(kappa_model)
    print(f'Successfully exported model into Kappa: {out_filename}')


def parse_to_gillespy(network_filename, language_filename, out_filename):
    mln_data = parse_mln(network_filename)
    language = parse_language_file(language_filename)

    tab = '\t'

    header_string = (
        f'import numpy\n'
        f'import matplotlib.pyplot as plt\n'
        f'from gillespy2.core import (\n'
        f'{tab}Model,\n'
        f'{tab}Species,\n'
        f'{tab}Reaction,\n'
        f'{tab}Parameter)\n\n'
        f'class Mln_dynamics(Model):\n'
        f'{tab}def __init__(self,parameter_values=None):\n'
        f'{tab * 2}Model.__init__(self, name="MLN")\n\n'
    )
    
    params = gillespie_parse_parameters(language)
    species = gillespie_parse_species(mln_data, language)
    reactions = gillespie_parse_reactions(mln_data, language)
    timespan = gillespie_parse_timespan(mln_data, language)
    footer = gillespie_parse_sim_options(mln_data, language)
    
    result = (
        header_string +
        params + '\n' +
        species + '\n' +
        reactions + '\n' +
        timespan + '\n' +
        footer
    )
    
    with open(out_filename, 'w') as f:
        f.write(result)
    
#     return result


def gillespie_parse_parameters(language):
    tab = '\t'
    params = []
    param_names = []
    
    for param in language['parameters']:
        name, value = param.split('=')
        param_names.append(name.strip())
        params.append(f"{tab}{tab}{name.strip()} = Parameter(name='{name}', expression={value})")
    
    params.append(f"{tab}{tab}self.add_parameter([{', '.join(param_names)}])\n")
    params = '\n'.join(params)
    
    return params


def gillespie_parse_species(mln_data, language):
    tab = '\t'
    species = []
    species_names = []
    
    for state in language['states']:
        for actor in mln_data['actors'][0]:
            species_names.append(f"{state}{actor}")
            init_value = 0
            for init_conditions in language['initial conditions']:
                name, value = init_conditions.split('=')
                if actor == name.strip() and state == value.strip():
                    init_value = 1
                    break
            species.append(f"{tab}{tab}{state}{actor} = Species(name='{state}{actor}', initial_value={init_value})")
    
    species.append(f"{tab}{tab}self.add_species([{', '.join(species_names)}])\n")
    species = '\n'.join(species)
    
    return species


def gillespie_parse_reactions(mln_data, language):
    tab = '\t'
    reactions = []
    reaction_names = []
    counter = 0
    
    for rule in language['rules']:
        nodes, rate = rule.split('@')
        rate = rate.strip()
        
        if '=' not in nodes:
            # a simple state-to-state rule for a single node
            left_node, right_node = nodes.split('->')
            left_node = left_node.strip()
            right_node = right_node.strip()
            
            for i in range(1, mln_data['actors'][1] + 1):
                name = f"{left_node}{i}_to_{right_node}{i}_{counter}"
                reaction = (
                    f"{tab * 2}{name} = Reaction(\n"
                    f"{tab * 4}name = '{name}',\n"
                    f"{tab * 4}rate = {rate},\n"
                    f"{tab * 4}reactants = {{{left_node}{i}: 1}},\n"
                    f"{tab * 4}products = {{{right_node}{i}: 1}}\n"
                    f"{tab * 3})\n"
                )
                
                reactions.append(reaction)
                reaction_names.append(name)
                counter += 1
        else:
            # two-node rule
            left_side, right_side = nodes.split('->')
            layer_index = int(left_side[left_side.index('=')+1].strip())
            
            left_reactant_1, left_reactant_2 = left_side.split(f"={layer_index}")
            right_reactant_1, right_reactant_2 = right_side.split(f"={layer_index}")
            
            left_reactant_1 = left_reactant_1.strip()
            left_reactant_2 = left_reactant_2.strip()
            right_reactant_1 = right_reactant_1.strip()
            right_reactant_2 = right_reactant_2.strip()
            
            for edge in mln_data['edges'][1][layer_index-1]:
                # note that this list already takes into account directionality of edges
                name = f"{left_reactant_1}{edge[0]}_{left_reactant_2}{edge[1]}_to_{right_reactant_1}{edge[0]}_{right_reactant_2}{edge[1]}_{counter}"
                reaction = (
                    f"{tab * 2}{name} = Reaction(\n"
                    f"{tab * 4}name = '{name}',\n"
                    f"{tab * 4}rate = {rate},\n"
                    f"{tab * 4}reactants = {{{left_reactant_1}{edge[0]}: 1, {left_reactant_2}{edge[1]}: 1}},\n"
                    f"{tab * 4}products = {{{right_reactant_1}{edge[0]}: 1, {right_reactant_2}{edge[1]}: 1}}\n"
                    f"{tab * 3})\n"
                )
                
                reactions.append(reaction)
                reaction_names.append(name)
                counter += 1
                
    
    reactions.append(f"{tab * 2}self.add_reaction([{', '.join(reaction_names)}])\n")
    reactions = '\n'.join(reactions)
    
    return reactions


def gillespie_parse_timespan(mln_data, language):
    tab = '\t'
    t_value = int(language['simOptions'][1].split('=')[1].strip())
    
    # note that below t_value is multiplied by 20 - I don't know why
    timespan = f"{tab * 2}self.timespan(numpy.linspace(0, {t_value}, {t_value * 20}))\n"
    
    return timespan


def gillespie_parse_sim_options(mln_data, language):
    tab = '\t'
    n_value = int(language['simOptions'][0].split('=')[1].strip())
    trajectories = [[] for i in range(len(language['views']))]
    trajectories_loop = []
    plots = []
    
    list_of_colours = ['b','g','r','c','m','y','k']
    active_colour = 0
    for i, view in enumerate(language['views']):
        appends = []
        for actor in mln_data['actors'][0]:
            appends.append(f"trajectory['{view}{actor}'][i]")
        
        appends = ' + '.join(appends)      
        trajectories_loop.append(f"{tab * 2}trajectories[{i}].append({appends})")
        
        plots.append(f"{tab}plt.plot(trajectory['time'], trajectories[{i}], '{list_of_colours[active_colour]}', label='{view}')")
        active_colour += 1
                           
    trajectories_loop = '\n'.join(trajectories_loop)
    plots = '\n'.join(plots)
                           
    footer = (
        f"def run_sim(model):\n"
        f"{tab}results = model.run(number_of_trajectories={n_value})\n"
        f"{tab}trajectory = results.average_ensemble()\n"
        f"{tab}plt.figure()\n"
        f"{tab}trajectories = {trajectories}\n"
        f"{tab}for i in range(len(trajectory['{language['views'][0]}1'])):\n"
        f"{trajectories_loop}\n"
        f"{plots}\n"
        f"{tab}plt.legend(loc='upper right')\n"
        f"{tab}plt.annotate(text=f'n = {n_value}', xy=(0.1, 0.9), xycoords='axes fraction')\n"
        f"{tab}plt.show()"
    )
    
    return footer
