# Importando funções e classes dos módulos específicos
from compiler.compile_smartcontract import compile_smartcontract
from blockchain.connection import connect_in_blockchain
from blockchain.connection import deploy_smartcontract
from fuzzer.genetic_fuzzer import genetic_fuzzer
from fuzzer.simulate_transaction import *
from contracts.source_map import SourceMap
from utils.low_level_calls import save_lowlevelcalls
from contracts.source_map import save_source_map
from fuzzer.mutation import *

from web3 import Web3
import random
import pprint
import json


if __name__ == "__main__":
    blockhain_url = "http://127.0.0.1:8545"
    contract_filename = "contracts/EtherStorev2.sol"
    contract_name = "EtherStore"
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
    
    # Connection and deploy
    w3_conn = connect_in_blockchain(blockhain_url)
    if w3_conn is not None:
        ether_store_contract = deploy_smartcontract(w3_conn, abi, bytecode)
    
    # Optional step, just for checking
    print("Depositing 1 Ether...")
    tx_receipt = simulate_transaction.simulate_transaction(w3=w3_conn, contract=ether_store_contract, function_name='deposit', value=Web3.to_wei(1, 'ether'))

    source_map = SourceMap(f"{contract_filename}:{contract_name}", compiler_output)
    save_source_map(compiler_output, contract_filename, contract_name, 'source_map.json')
    if tx_receipt is not None:
        print("Contract balance: {}".format(ether_store_contract.functions.getBalance().call()))
        initial_analysis = {
            "sloads": sloads,
            "calls": calls,
            "source_map": source_map
        }

        #genetic_fuzzer(abi, bytecode, ether_store_contract.address, initial_analysis, generations=10, population_size=10)

        auth_addresses = w3_conn.eth.accounts[:3]

        print("\n[*] Gerando mapa de acessos a slots de armazenamento...")
        fn_access_map = map_function_state_accesses(bytecode, abi)
        pprint.pprint(fn_access_map)

        print("\n[*] Inferindo dependências def-use...")
        dependencies = infer_data_flow_dependencies(fn_access_map)
        pprint.pprint(dependencies)

        print("\n[*] Gerando sequência ordenada de chamadas com base nas dependências...")
        sequence = []
        ordered_fns = sorted(dependencies.keys())  # Pode usar generate_ordered_sequence() também

        for fn in ordered_fns:
            seed = generate_seed(ether_store_contract, fn, auth_addresses)
            sequence.append(seed)

        print("\n[*] Sequência inicial:")
        pprint.pprint(sequence)

        print("\n[*] Mutando uma seed aleatória da sequência...")
        random_index = random.randint(0, len(sequence)-1)
        mutated_seq, mutated_seed = mutate_seed(sequence[random_index], auth_addresses)
        print(f"\nFunção original: {sequence[random_index]['function']}")
        print("[*] Seed mutada:")
        pprint.pprint(mutated_seed)

        print("\n[*] Sequência com mutação de ordem/transações:")
        seq_mutada = mutate_transaction_sequence(sequence)
        pprint.pprint(seq_mutada)

        print("\n[*] Executando symbolic feedback na primeira função...")
        observed_def_use = {}
        feedback = symbolic_execution_feedback(
            w3=w3_conn,
            contract=ether_store_contract,
            function_name=sequence[0]['function'],
            inputs=sequence[0]['inputs'],
            sender=sequence[0]['sender'],
            function_access_map=fn_access_map,
            observed_def_use=observed_def_use
        )
        pprint.pprint(feedback)

        print("\n[*] Aplicando guided mutation com base no feedback simbólico...")
        guided_seq = guided_mutation_based_on_feedback(sequence, feedback, dependencies)
        pprint.pprint(guided_seq)

        

    

