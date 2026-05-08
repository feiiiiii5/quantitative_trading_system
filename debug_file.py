
with open('core/simulated_trading.py', 'rb') as f:
    data = f.read()

# Find the approximate location of import_portfolio
target_str = b"def import_portfolio"
pos = data.find(target_str)
if pos == -1:
    print("not found")
else:
    print(f"Found at position {pos}")
    # Read 1000 bytes around there
    chunk = data[max(0, pos-200):pos+2000]
    print("\nHex dump:")
    for i in range(0, len(chunk), 16):
        hex_part = " ".join(f"{b:02x}" for b in chunk[i:i+16])
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk[i:i+16])
        print(f"{i:04x}  {hex_part:<48}  |{ascii_part}|")

    # Now try to parse line by line
    print("\nLine by line around there:")
    lines = data.split(b'\n')
    start_line = 0
    for i, line in enumerate(lines):
        if target_str in line:
            start_line = max(0, i - 10)
            end_line = min(len(lines), i + 100)
            for j in range(start_line, end_line):
                print(f"{j+1:4d}: {lines[j]!r}")
            break
