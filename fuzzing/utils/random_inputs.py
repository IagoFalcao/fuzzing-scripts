import random
import struct
import json
import os

# AFL Mutations
def generate_random_buffer():
    size = random.randint(1, 256)
    return bytearray(random.randint(0, 255) for _ in range(size))

def flip_bits(buffer):
    num_bits = random.randint(0, len(buffer) * 8)
    for _ in range(num_bits):
        bit_pos = random.randint(0, len(buffer) * 8 - 1)
        buffer[bit_pos // 8] ^= (1 << (bit_pos % 8))
    return buffer

def set_interesting_values(buffer):
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

def delete_bytes(buffer):
    if len(buffer) <= 1:
        return buffer
    del_len = random.randint(1, len(buffer) // 2)
    del_pos = random.randint(0, len(buffer) - del_len)
    del buffer[del_pos:del_pos + del_len]
    return buffer

def duplicate_bytes(buffer):
    max_size = 1024
    if len(buffer) >= max_size or len(buffer) <= 1:
        return buffer
    dup_len = random.randint(1, len(buffer) // 2)
    dup_pos = random.randint(0, len(buffer) - dup_len)
    if len(buffer) + dup_len > max_size:
        dup_len = max_size - len(buffer)
    buffer.extend(buffer[dup_pos:dup_pos + dup_len])
    return buffer

def insert_random_bytes(buffer):
    max_size = 1024
    if len(buffer) >= max_size:
        return buffer
    insert_len = random.randint(1, max_size - len(buffer))
    insert_pos = random.randint(0, len(buffer))
    random_bytes = bytearray(random.randint(0, 255) for _ in range(insert_len))
    buffer[insert_pos:insert_pos] = random_bytes
    return buffer

def add_subtract_random(buffer):
    if not buffer:
        return buffer
    pos = random.randint(0, len(buffer) - 1)
    change = random.randint(-10, 10)
    buffer[pos] = (buffer[pos] + change) % 256
    return buffer

def mutate_input(buffer):
    mutation = random.randint(1, 6)
    if mutation == 1:
        return flip_bits(buffer)
    elif mutation == 2:
        return add_subtract_random(buffer)
    elif mutation == 3:
        return set_interesting_values(buffer)
    elif mutation == 4:
        return duplicate_bytes(buffer)
    elif mutation == 5:
        return insert_random_bytes(buffer)
    elif mutation == 6:
        return delete_bytes(buffer)

# parse inputs to bytearray
def serialize_inputs(inputs):
    result = bytearray()
    for value in inputs.values():
        if isinstance(value, int):
            result += value.to_bytes(32, byteorder='big', signed=False)
        elif isinstance(value, str) and value.startswith("0x"):
            result += bytearray.fromhex(value[2:])
        elif isinstance(value, str):
            result += value.encode()
        elif isinstance(value, bool):
            result += b'\x01' if value else b'\x00'
        else:
            result += bytearray(str(value), 'utf-8')
    return result

# Gera inputs + mutações
def generate_random_inputs(abi):
    inputs = []

    for item in abi:
        if item['type'] == 'function' and item['name'] != 'balances': 
            function_inputs = dict()
            for input_param in item.get('inputs', []):
                param_type = input_param['type']
                if param_type == 'uint256':
                    value = random.randint(0, 2**256 - 1)
                elif param_type == 'address':
                    value = '0x' + ''.join(random.choices('0123456789abcdef', k=40))
                elif param_type == 'string':
                    value = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', k=random.randint(5, 15)))
                elif param_type == 'bool':
                    value = random.choice([True, False])
                elif param_type.startswith('bytes'):
                    size = int(param_type.replace('bytes', '')) if len(param_type) > 5 else random.randint(1, 32)
                    value = '0x' + ''.join(random.choices('0123456789abcdef', k=size*2))
                else:
                    value = None
                if value is not None:
                    function_inputs[input_param['name']] = value

            if function_inputs:
                buffer = serialize_inputs(function_inputs)
            else:
                buffer = generate_random_buffer()

            mutated_buffer = mutate_input(buffer)

            inputs.append({
                'stateMutability': item["stateMutability"],
                'name': item['name'],
                'inputs': function_inputs,
                'mutated': mutated_buffer.hex()
            })
    save_testcases(inputs)
    return inputs

# Salva em JSON
def save_testcases(testcases):
    os.makedirs('./output', exist_ok=True)
    with open('./output/testcases.json', 'w') as f:
        json.dump(testcases, f, indent=4)


