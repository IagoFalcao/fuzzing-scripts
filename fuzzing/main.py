# Importando funções e classes dos módulos específicos
from compiler.compile_smartcontract import *
from blockchain.connection import *
from fuzzer.genetic_fuzzer import *
from fuzzer.simulate_transaction import *
from contracts.source_map import *
from utils.low_level_calls import *
from utils.random_inputs import *
from contracts.source_map import *


from web3 import Web3
import random
import pprint
import json
import os


if __name__ == "__main__":
    blockhain_url = "http://127.0.0.1:8545"
    contract_filename = "fuzzing/contracts/FuzzTestContract.sol"
    
    contract_name = "FuzzTestContract"
    solc_version = "0.8.24"

    sloads = dict()
    calls = set()

    with open(contract_filename, 'r') as file:
        source_code = file.read()
    
    compiler_output = compile_smartcontract(solc_version, contract_filename, source_code)
    
    # Smart contract information
    contract_interface = compiler_output['contracts'][contract_filename][contract_name]
    abi = contract_interface['abi']
    bytecode = contract_interface['evm']['bytecode']['object']
    deployed_bytecode = contract_interface['evm']['deployedBytecode']['object']

    #Sve abi for checking
    os.makedirs('output',exist_ok=True)
    abi_output_filename = 'output/abi.json'
    with open(abi_output_filename, 'w') as f:
        json.dump(abi, f, indent=4)

    
    
    # Connection and deploy
    w3_conn = connect_in_blockchain(blockhain_url)
    if w3_conn is not None:
        ether_store_contract = deploy_smartcontract(w3_conn, abi, bytecode)
    
   
    source_map = SourceMap(f"{contract_filename}:{contract_name}", compiler_output)
    
    save_source_map(compiler_output, contract_filename, contract_name, 'output/source_map.json')
    genetic_fuzzer(w3_conn, abi, ether_store_contract, sloads, calls,source_map) # Init Fuzzing proccess
    
    
        
       