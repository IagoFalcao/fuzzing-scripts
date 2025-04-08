import subprocess
import json
import os
import solcx
from compiler import compile_smartcontract

# Function to compile the contract and return his AST

def generate_ast(compiler_output) -> dict:
    # Print keys in compiler_output for debugging
    print("Compiler output structure debug:")
    for contract_path, contract_data in compiler_output['contracts'].items():
        print(f"Contract Path: {contract_path}, Keys: {list(contract_data.keys())}")

    # Extract contract filename
    contract_filename = list(compiler_output['contracts'].keys())[0]
    print(f"Contract Filename: {contract_filename}")

    # Extract contract name
    contract_data = compiler_output['contracts'][contract_filename]
    contract_name = list(contract_data.keys())[0]
    print(f"Contract Name: {contract_name}")

    # Access contract-specific data
    contract_details = contract_data[contract_name]

    # Check for the 'evm' key
    if "evm" not in contract_details:
        raise KeyError(f"'evm' key is missing in the contract data for {contract_filename}:{contract_name}")

    # Check for the 'legacyAssembly' key
    if "legacyAssembly" not in contract_details["evm"]:
        raise KeyError(f"'legacyAssembly' key is missing in 'evm' for {contract_filename}:{contract_name}")

    # Extract and save AST
    ast_json = contract_details["evm"]["legacyAssembly"]
    print(f"AST successfully extracted for {contract_filename}:{contract_name}")
    return ast_json
#For now, isnert the assert verification in every function call
# that way we can see where the code have been executed and improve the coverage

# nodes in Solidity represent the structure and components of your smart contract source code.
# Each node corresponds to a specific part of the contract 

def add_verification_to_function(node):
    #Adds an assert (for now) at the top of every function
    # Checks if the current node represents a function
    if isinstance(node, dict):
        #print(f"Proccessing node: {node}") #debug

        if 'nodeType' in node: #check if has a nodetype key



            if node['nodeType'] == 'FunctionDefinition':
                    # Insert verification at the beginning of each function body 
                    #  Some functions, such as abstract functions or interfaces, might lack a body. 
                    #  Trying to insert statements into a non-existent body would result in an error.
                    if 'body' in node:
                        verification_code = {
                            #equivalent to writing assert(true)
                            "nodeType": "ExpressionStatement",
                            "expression": {
                                "nodeType": "FunctionCall",
                                "functionName": "assert",
                                "arguments": [{"nodeType": "Literal", "value": "true"}]  # Simple assert(true) for demo
                            }
                        }
                        node['body']['statements'].insert(0, verification_code)
        # cThis update adds a check to make sure the node is a dictionary and that the nodeType exists before accessing it.
        #  Additionally, it ensures that if there are nested dictionaries or lists (like in an AST), those are also processed.
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value,list):
                    for item in value:
                        add_verification_to_function(item)
        else: print(f"Error, missing 'nodeType' at node {node}")


    return node
# traverse, analyze, and modify the AST in a structured way.
def process_node(node):
    #process nodes children(body,statements)
    if 'nodes' in node:
         for i, child_node in enumerate(node['nodes']):
           node['nodes'][i] = process_node(child_node)
    return add_verification_to_function(node)


def modify_AST(ast_json):
    modified_ast_json = process_node(ast_json)
    output_filename = 'output/modified_ast.json'
    with open(output_filename, 'w') as f:
        json.dump(modified_ast_json, f, indent=2)
    return modified_ast_json


def generate_ir_from_ast(ast_json, contract_filename, output_dir="output", solc_version="0.8.0"):

    #ensure the compiler version is installed
    if solc_version not in solcx.get_installable_solc_versions():
        solcx.install_solc(solc_version)
    solcx.get_solc_version()

    #Save the modified ast
    modified_ast_path = os.path.join(output_dir,'modified_ast.json')
    os.makedirs(output_dir,exist_ok=True)
    with open(modified_ast_path, "w") as f:
        json.dump(ast_json, f, indent=2)
    #import compile_smartcontract
    #Generate IR with solc
    try:
        ir_output = compile_smartcontract({
            "language": "Solidity",
            "sources": {
                contract_filename: {"content": ""}
            },
            "settings": {
                "optimizer": {"enabled": True, "runs": 200},
                "outputSelection": {
                    "*": {
                        "*": ["evm.legacyAssembly"]  # This generates the Yul Assembly IR
                    }
                }
            }
        }, allow_paths=".")
        #extract generated ir
        ir_code = ir_output['contracts'][contract_filename]['*']["evm"]['legacyAssembly']

        ir_file_path = os.path.join(output_dir, "contract_ir.yul")
        with open(ir_file_path, "w") as f:
            f.write(ir_code)

        print(f"IR generated and saved to: {ir_file_path}")
        

        # Instrument the IR code
        instrumented_ir = instrument_ir(ir_code)
        
        # Save the instrumented IR to a file
        instrumented_ir_file_path = os.path.join(output_dir, "instrumented_contract_ir.yul")
        with open(instrumented_ir_file_path, "w") as f:
            f.write(instrumented_ir)
        
        print(f"Instrumented IR generated and saved to: {ir_file_path}")
        return ir_code
    except Exception as e:
        print(f"Error generating IR: {e}")
        return None


def instrument_ir(ir_code: str):

    #split the ir code into separated lines
    ir_lines = ir_code.splitlines()
    instrumented_lines = []

    for line in ir_lines:
        #inserting an assert statement before each function
        if 'function' in line.lower():#if is a function will appear function at tghe yul
            instrumented_lines.append('assert(true); //track function entry')
        instrumented_lines.append(line)

    #join the lines back together
    instrument_ir = '\n'.join(instrumented_lines)
    
    return instrument_ir
