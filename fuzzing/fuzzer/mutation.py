import json
import hashlib
import random
from web3 import Web3
from eth_account import Account
from eth_tester import EthereumTesterProvider
from web3.providers.eth_tester import EthereumTesterProvider
from copy import deepcopy
from utils.random_inputs import mutate_input
from collections import defaultdict
from fuzzer import simulate_transaction
#Fun to calculate the 'selector' of a function (the first 4 bytes of keccak256) 
# #to trigger wich function was called

def keccak_selector(signature):#signatrure eg transfer(address,uint256)
    return hashlib.new('sha3_256',signature.encode()).hexdigest()[:8]

#Func that maps wich functions acess storage slots
#use later for reentrancy---------------------------
def map_function_state_accesses(bytecode,abi):
    function_map = {}
    bytecode = bytecode.lower().replace("0x","")#no prefixes in bytecode

    for function in abi:
        if function.get("type") != "function":
            continue #ignore constructors, fallback, etc

        #builds function signature
        function_name = function["type"]
        inputs = function["inputs"]
        arg_types = ",".join([i["type"] for i in inputs])
        signature = f"{function_name} ({arg_types})"

        #calculates the evm selector
        selector = keccak_selector(signature)
        
        #search this selector in bytecode
        index = bytecode.find(selector)
        if index == -1:
            continue #skip if not in bytecode

        state_reads = []
        state_writes = []

        #find a instruction block of the function

        for i in range(index,min(len(bytecode),index - 400),2): #reads 1 byte
            opcode = bytecode[i:i+2]
            if opcode == "54": 
                #opcode54 = sload (read)
                state_reads.append(f"slot_{i//2}")
            elif opcode =="55":
                #opcode55 = sstore (write)
                state_writes.append(f"slot_{i//2}")
        
        function_map[function_name] = {
            "reads": state_reads,
            "writes": state_writes
        }
    return function_map

#Func to detect def-use dependencies
"""
In Solidity, Def-Use (Definition-Use) dependencies help analyze how 
variables and state changes propagate through a smart contract. 
Since Solidity contracts handle financial transactions and immutable code, 
understanding these dependencies is crucial for preventing reentrancy
"""
def infer_data_flow_dependencies(function_access_map):
    dependencies = {}

    #Functions and slots that writes
    for fn_writer, access in function_access_map.items():
        writes = set(access["writes"])

        #Compare to other functios to trigger the reads
        for fn_reader,reader_access in function_access_map.items():
            reads = set(reader_access["reads"])

            #If there is intersection between them, there is dependency
            if writes & reads:
                #Adds fn_reader as fn_writer dependent
                if fn_writer not in dependencies:
                    dependencies[fn_writer] = []
                dependencies[fn_writer].append(fn_reader)
    return dependencies

#Func to check sender verifications 
def detect_auth_checks(bytecode):
    auth_checks = []
    bytecode  = bytecode.lower().replace("0x","")
    i = 0
    
    while i < len(bytecode) -44: #44 chars = 22bytes (33 + push20 + 14)
        opcode = bytecode[i:i+2]
        next_opcode = bytecode[i+2:i+4]

        #checks caller (0x33) followed by push20 (0x73)

        if opcode == "33" and next_opcode == "73":
            address_hex = bytecode[i+4:i+44]# 20 bytes
            eq_opcode = bytecode[i+44:i+46]
            if eq_opcode == "14": #EQ
                auth_checks.append(f"msg.sender == {address_hex}")
        i += 2
    return auth_checks


def generate_random_input(param_type):
    if param_type.startswith("uint"):
        return random.randint(0, 2**256 - 1)
    elif param_type.startswith("int"):
        return random.randint(-2**255, 2**255 - 1)
    elif param_type == "address":
        return "0x" + "".join(random.choices("0123456789abcdef", k=40))
    elif param_type == "bool":
        return random.choice([True, False])
    elif param_type.startswith("bytes"):
        size = int(param_type[5:]) if param_type != "bytes" else random.randint(1, 32)
        return bytes(random.getrandbits(8) for _ in range(size))
    elif param_type == "string":
        return ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
    else:
        return None  # tipos complexos não tratados ainda

def generate_seed(contract,function, auth_address):
    inputs = {}
    fn_abi = contract.get_fuction_by_name(function).abi

    for param in fn_abi['inputs']:
        inputs[param['name']] = generate_random_input(param[type])

    #sender random choice
    sender = random.choice(auth_address) if auth_address else contract.web3.eth.accounts[0]

    value = random.randint(1, 5) * 10**15 if random.random() < 0.3 else 0

    return {"function": function, "inputs": inputs, "sender": sender, "value": value}

#Generatinh ordered calss sequence acording to dependencies

def generate_ordered_sequence(dependencies):
    ordered = []
    visited = set()

    def dfs(fn):
        if fn in visited:
            return
        visited.add(fn)
        for dep in dependencies.get(fn, []):
            dfs(dep)
        ordered.append(fn)

    for fn in dependencies:
        dfs(fn)

    return ordered[::-1]  # reverse para garantir ordem de execução correta

#exchange transactions order
def mutate_transaction_sequence(sequence):
    #Modify the transaction sequences, including adding or removing
    mutated_sequence = deepcopy(sequence)

    mutation_type = random.choice(["permutation","insertion","deletion"])

    if mutation_type == "permutation"and len(mutated_sequence) > 1:
        #random exchange between sequence's transaction
        index1,index2 = random.sample(range(len(mutated_sequence)),2)
        mutated_sequence[index1],mutated_sequence[index2] = mutated_sequence[index2],mutated_sequence[index1]

    elif mutation_type == "insertion":
        #inserts a random fake transaction in the sequence

        random_function = random.choice(sequence)
        mutated_sequence.insert(random.randint(0,len(mutated_sequence)),random)
    
    elif mutation_type == "deletion":
        #deletes a random transaction
        mutated_sequence.pop(random.randint(0,len(mutated_sequence) - 1))
    
    return mutated_sequence

#func that mtates transaction's sender address
def mutate_sender(sender,auth_addresses):
    if len(auth_addresses) > 1:#select a authentic address to replace the current sender
        return random.choice([addr for addr in auth_addresses if addr != sender])
    return sender

#Func to mutate seeds(function, inputs, sender)
def mutate_seed(seed,auth_addresses):

    #sender mutation
    seed["sender"] = mutate_sender(seed["sender"],auth_addresses)

    #input mutation
    mutated_inputs = {}
    for param,value in seed["inputs"].items():
        mutated_inputs[param] = mutate_input(value)
    seed["inputs"] = mutated_inputs

    #transaction mutation
    mutated_sequence = mutate_transaction_sequence([seed["function"]])

    return mutated_sequence,seed


# Função para verificar se um def-use chain é novo com base no histórico
def is_new_def_use(function_name, state_reads, state_writes, observed_def_use):
    new_paths = []

    for write in state_writes:
        for read_fn, read_slots in observed_def_use.items():
            if write in read_slots and read_fn != function_name:
                new_paths.append((function_name, read_fn, write))
    
    return new_paths
def symbolic_execution_feedback(w3, contract, function_name, inputs, sender, function_access_map, observed_def_use):
    feedback = defaultdict(list)

    txn_receipt = simulate_transaction(w3, contract, function_name, inputs, sender)

    if txn_receipt is None:
        print(f"Failed to execute function {function_name}")
        return feedback

    # memories access
    access = function_access_map.get(function_name, {})
    state_reads = access.get("reads", [])
    state_writes = access.get("writes", [])

    # Update feedback if new def_use is detected
    new_def_uses = is_new_def_use(function_name, state_reads, state_writes, observed_def_use)

    for def_fn, use_fn, slot in new_def_uses:
        feedback["def_use_chains"].append({
            "defined_in": def_fn,
            "used_in": use_fn,
            "slot": slot
        })

    # Atualiza o mapa de slots lidos por função
    if function_name not in observed_def_use:
        observed_def_use[function_name] = set()
    observed_def_use[function_name].update(state_reads)

    return feedback

def guided_mutation_based_on_feedback(sequence,feedback,def_use_graph):
    mutated_sequence = deepcopy(sequence)


    #More priority to new def-use functions
    for def_use in feedback.get("def_use_chains",[]):
        use_fn = def_use["used_in"]
        if use_fn not in [tx["function"] for tx in sequence]:
            #adds the new func
            mutated_sequence.append({"function": use_fn, "inputs": {}, "sender": None, "value": 0})
    ordered_sequence = []
    visited = set()

    def dfs(fn):
        if fn in visited:
            return
        visited.add(fn)
        for dep in def_use_graph.get(fn,[]):
            dfs(dep)
        ordered_sequence.append(fn)

    for tx in mutated_sequence:
        dfs(tx["function"])

    #Rebuilds sequence in order
    final_sequence = []
    for fn in ordered_sequence:
        for tx in mutated_sequence:
            if tx["function"] == fn:
                final_sequence.append(tx)
                break
    return final_sequence
