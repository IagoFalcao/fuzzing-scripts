import random
import struct
import json
import os
from typing import Any, Dict, List, Union
os.makedirs('./output', exist_ok=True)
def generate_random_inputs(abi: List[Dict]) -> Dict[str, List[Dict]]:
    functions_with_inputs = []
    functions_without_inputs = []
    
    for item in abi:
        if item['type'] != 'function':
            continue
            
        function_data = {
            'name': item['name'],
            'stateMutability': item.get('stateMutability', 'nonpayable'),
            'inputs': []
        }

        if not item.get('inputs'):
            # Para funções sem inputs, geramos 5 mutações diferentes
            mutations = [
                {'type': 'raw_bytes', 'value': mutate_raw_input(), 'mutation_type': 'flip_bits'},
                {'type': 'raw_bytes', 'value': mutate_raw_input(), 'mutation_type': 'interesting_values'},
                {'type': 'raw_bytes', 'value': mutate_raw_input(), 'mutation_type': 'delete_bytes'},
                {'type': 'raw_bytes', 'value': mutate_raw_input(), 'mutation_type': 'duplicate_bytes'},
                {'type': 'raw_bytes', 'value': mutate_raw_input(), 'mutation_type': 'add_subtract'}
            ]
            function_data['inputs'] = mutations
            functions_without_inputs.append(function_data)
        else:
            # Para funções com inputs, geramos 3 mutações por parâmetro
            param_mutations = []
            for input_param in item['inputs']:
                param_type = input_param['type']
                original_value = generate_typed_value(param_type)
                
                mutations = [
                    {
                        'name': input_param['name'],
                        'type': param_type,
                        'original_value': original_value,
                        'mutated_value': mutate_typed_value(original_value, param_type),
                        'mutation_type': 'type_specific_1'
                    },
                    {
                        'name': input_param['name'],
                        'type': param_type,
                        'original_value': original_value,
                        'mutated_value': mutate_typed_value(original_value, param_type),
                        'mutation_type': 'type_specific_2'
                    },
                    {
                        'name': input_param['name'],
                        'type': param_type,
                        'original_value': original_value,
                        'mutated_value': mutate_typed_value(original_value, param_type),
                        'mutation_type': 'type_specific_3'
                    }
                ]
                param_mutations.append(mutations)
            
            # 
            for i in range(3):  # Para cada conjunto de mutações
                combined_inputs = []
                for param in param_mutations:
                    combined_inputs.append(param[i])
                
                mutated_function = function_data.copy()
                mutated_function['inputs'] = combined_inputs
                functions_with_inputs.append(mutated_function)
    
    return {
        'functions_with_inputs': functions_with_inputs,
        'functions_without_inputs': functions_without_inputs,
        'metadata': {
            'mutation_types_used': {
                'raw_bytes': ['flip_bits', 'interesting_values', 'delete_bytes', 'duplicate_bytes', 'add_subtract'],
                'typed_inputs': ['numeric', 'address', 'string', 'bytes']
            },
            'total_mutations_generated': len(functions_with_inputs)*3 + len(functions_without_inputs)*5
        }
    }

def mutate_raw_input() -> str:
    mutation_type = random.choice([
        ('flip_bits', flip_bits),
        ('interesting_values', set_interesting_values),
        ('delete_bytes', delete_bytes),
        ('duplicate_bytes', duplicate_bytes),
        ('add_subtract', add_subtract_random)
    ])
    mutated = mutation_type[1]()
    return {
        'value': '0x' + mutated.hex(),
        'mutation_method': mutation_type[0]
    }

def generate_typed_value(param_type: str) -> Union[int, str, bool, bytes]:
    """Gera valor inicial baseado no tipo"""
    if param_type == 'uint256':
        return random.randint(0, 2**256 - 1)
    elif param_type == 'address':
        return '0x' + ''.join(random.choices('0123456789abcdef', k=40))
    elif param_type == 'bool':
        return random.choice([True, False])
    elif param_type == 'string':
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(5, 20)))
    elif param_type.startswith('bytes'):
        size = int(param_type[5:]) if len(param_type) > 5 else random.randint(1, 32)
        return bytes(random.randint(0, 255) for _ in range(size))
    elif param_type.startswith('int'):
        bits = int(param_type[3:]) if len(param_type) > 3 else 256
        return random.randint(-2**(bits-1), 2**(bits-1) - 1)
    else:
        return None

def mutate_typed_value(value: Union[int, str, bool, bytes], param_type: str) -> Union[int, str, bool, bytes]:
    """Aplica mutação baseada no tipo do parâmetro"""
    if param_type == 'uint256' or param_type.startswith('int'):
        return apply_numeric_mutation(value)
    elif param_type == 'address':
        return apply_address_mutation(value)
    elif param_type == 'bool':
        return not value
    elif param_type == 'string':
        return apply_string_mutation(value)
    elif param_type.startswith('bytes'):
        return apply_bytes_mutation(value)
    return value

def apply_numeric_mutation(value: int) -> int:
    mutations = [
        value + 1,
        value - 1,
        value * 2,
        value // 2,
        0,
        2**256 - 1,
        random.randint(0, 2**256 - 1)
    ]
    return random.choice(mutations)

def apply_address_mutation(address: str) -> str:
    mutations = [
        '0x' + '0'*40,  # Endereço zero
        '0x' + 'f'*40,  # Endereço máximo
        address[:-4] + 'dead',  # Modifica final
        '0x' + ''.join(random.choices('0123456789abcdef', k=40))  # Novo aleatório
    ]
    return random.choice(mutations)

def apply_string_mutation(s: str) -> str:
    if not s:
        return s
        
    mutations = [
        s.upper(),
        s[::-1],
        s + s,
        s[:len(s)//2],
        ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=len(s)))
    ]
    return random.choice(mutations)

def apply_bytes_mutation(b: bytes) -> bytes:
    mutated = bytearray(b)
    if random.random() < 0.5:
        # Mutação estrutural
        if len(mutated) > 1 and random.random() < 0.3:
            del mutated[random.randint(0, len(mutated)-1)]
        if random.random() < 0.3:
            mutated.append(random.randint(0, 255))
    else:
        # Mutação de valor
        pos = random.randint(0, len(mutated)-1)
        mutated[pos] = (mutated[pos] + random.randint(-10, 10)) % 256
    return bytes(mutated)
#AFL mutations
def generate_random_buffer():
    size = random.randint(1, 256)
    return bytearray(random.randint(0, 255) for _ in range(size))

def flip_bits():
    buffer = generate_random_buffer()
    num_bits = random.randint(0, len(buffer) * 8)
    for _ in range(num_bits):
        bit_pos = random.randint(0, len(buffer) * 8 - 1)
        buffer[bit_pos // 8] ^= (1 << (bit_pos % 8))
    return buffer

def set_interesting_values():
    buffer = generate_random_buffer()
    interesting_8 = [0x00, 0xFF, 0x7F]
    interesting_16 = [0x0000, 0xFFFF, 0x7FFF]
    interesting_32 = [0x00000000, 0xFFFFFFFF, 0x7FFFFFFF]
    
    pos = random.randint(0, len(buffer) - 1)
    choice = random.randint(0, 2)

    if choice == 0:
        buffer[pos] = random.choice(interesting_8)
    elif choice == 1 and pos + 1 < len(buffer):
        buffer[pos:pos+2] = struct.pack('<H', random.choice(interesting_16))
    elif choice == 2 and pos + 3 < len(buffer):
        buffer[pos:pos+4] = struct.pack('<I', random.choice(interesting_32))
    return buffer

def delete_bytes():
    buffer = generate_random_buffer()
    if len(buffer) <= 1:
        return buffer
    del_len = random.randint(1, len(buffer) // 2)
    del_pos = random.randint(0, len(buffer) - del_len)
    del buffer[del_pos:del_pos + del_len]
    return buffer

def duplicate_bytes():
    max_size = 1024
    buffer = generate_random_buffer()
    if len(buffer) >= max_size or len(buffer) <= 1:
        return buffer
    dup_len = random.randint(1, len(buffer) // 2)
    dup_pos = random.randint(0, len(buffer) - dup_len)
    if len(buffer) + dup_len > max_size:
        dup_len = max_size - len(buffer)
    buffer.extend(buffer[dup_pos:dup_pos + dup_len])
    return buffer

def insert_random_bytes():
    max_size = 1024
    buffer = generate_random_buffer()
    if len(buffer) >= max_size:
        return buffer
    insert_len = random.randint(1, max_size - len(buffer))
    insert_pos = random.randint(0, len(buffer))
    random_bytes = bytearray(random.randint(0, 255) for _ in range(insert_len))
    buffer[insert_pos:insert_pos] = random_bytes
    return buffer

def add_subtract_random():
    buffer = generate_random_buffer()
    if not buffer:
        return buffer
    pos = random.randint(0, len(buffer) - 1)
    change = random.randint(-10, 10)
    buffer[pos] = (buffer[pos] + change) % 256
    return buffer

def mutate_input():
    mutation = random.randint(1, 6)
    if mutation == 1:
        return flip_bits()
    elif mutation == 2:
        return add_subtract_random()
    elif mutation == 3:
        return set_interesting_values()
    elif mutation == 4:
        return duplicate_bytes()
    elif mutation == 5:
        return insert_random_bytes()
    elif mutation == 6:
        return delete_bytes()
    
def save_mutations(mutations: Dict[str, Any]):
    """Salva os resultados em ../output/mutations.json"""
    output_path = os.path.join('..', 'output', 'mutations.json')
    with open(output_path, 'w') as f:
        json.dump(mutations, f, indent=2, ensure_ascii=False)
    print(f'Mutações salvas em {output_path}')

