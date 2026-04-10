import subprocess
import sys
import time
import argparse
import json
import os
import re

def run_single_test(test_file, modified=False, visualize=False):
    """
    Запускает steiner.py для одного теста и возвращает словарь с результатами.
    """
    cmd = [sys.executable, "steiner.py"]
    if modified:
        cmd.append("-m")
    if visualize:
        cmd.append("-v")
    cmd.append(test_file)
    
    start = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    
    if result.returncode != 0:
        print(f"Error running test {test_file}:")
        print(result.stderr)
        return None
    
    stdout = result.stdout
    info = {}
    
    match = re.search(r'Algorithm:\s*(.+)', stdout)
    if match:
        info["algorithm"] = match.group(1).strip()
    
    match = re.search(r'Initial MST length:\s*(\d+)', stdout)
    if match:
        info["initial_len"] = int(match.group(1))
    
    match = re.search(r'Final Steiner tree length:\s*(\d+)', stdout)
    if match:
        info["final_len"] = int(match.group(1))
    
    match = re.search(r'Improvement:\s*(\d+)\s*\((\d+\.?\d*)%\)', stdout)
    if match:
        info["improvement"] = int(match.group(1))
        info["improvement_percent"] = float(match.group(2))
    
    match = re.search(r'Time:\s*(\d+\.?\d*)\s*s', stdout)
    if match:
        info["time_alg"] = float(match.group(1))
    
    match = re.search(r'Points:\s*(\d+)\s*\(Terminals:\s*(\d+),\s*Steiner:\s*(\d+)\)', stdout)
    if match:
        info["total_points"] = int(match.group(1))
        info["terminals"] = int(match.group(2))
        info["steiners"] = int(match.group(3))
    
    match = re.search(r'Edges:\s*(\d+)', stdout)
    if match:
        info["edges"] = int(match.group(1))
    
    info["exec_time"] = elapsed
    return info

def main():
    parser = argparse.ArgumentParser(description="Run multiple Steiner tree tests (both basic and modified)")
    parser.add_argument("-n", "--num-tests", type=int, required=True,
                        help="Number of tests to run (test0.json ... testN-1.json)")
    parser.add_argument("--csv", type=str, help="Save results to CSV file")
    args = parser.parse_args()
    
    results = []
    
    # Заголовок таблицы с новыми столбцами
    print(f"\n{'='*140}")
    print(f"{'Test':<8} {'Term':<5} {'Init':<6} {'Basic':<8} {'Basic':<8} {'St':<4} {'Mod':<8} {'Mod':<8} {'St':<4} {'Speedup':<10} {'Impr':<6}")
    print(f"{'':8} {'':5} {'MST':<6} {'Final':<8} {'Time(s)':<8} {'(B)':<4} {'Final':<8} {'Time(s)':<8} {'(M)':<4} {'Basic/Mod':<10} {'%':<6}")
    print(f"{'-'*140}")
    
    for i in range(args.num_tests):
        test_file = f"test{i}.json"
        if not os.path.exists(test_file):
            print(f"Warning: {test_file} not found, skipping")
            continue
        
        print(f"{test_file:<8}", end=" ", flush=True)
        
        info_mod = run_single_test(test_file, modified=True, visualize=False)
        if info_mod is None:
            print(" MOD_FAILED")
            continue
        
        info_basic = run_single_test(test_file, modified=False, visualize=False)
        if info_basic is None:
            print(" BASIC_FAILED")
            continue
        
        speedup = info_basic['time_alg'] / info_mod['time_alg'] if info_mod['time_alg'] > 0 else 0
        
        print(f"{info_basic['terminals']:<5} {info_basic['initial_len']:<6} "
              f"{info_basic['final_len']:<8} {info_basic['time_alg']:<8.4f} "
              f"{info_basic['steiners']:<4} "
              f"{info_mod['final_len']:<8} {info_mod['time_alg']:<8.4f} "
              f"{info_mod['steiners']:<4} "
              f"{speedup:<10.2f}x {info_basic['improvement_percent']:<6.1f}%")
        
        results.append({
            "test": test_file,
            "terminals": info_basic['terminals'],
            "initial_len": info_basic['initial_len'],
            "basic_final_len": info_basic['final_len'],
            "basic_time": info_basic['time_alg'],
            "basic_steiners": info_basic['steiners'],
            "mod_final_len": info_mod['final_len'],
            "mod_time": info_mod['time_alg'],
            "mod_steiners": info_mod['steiners'],
            "speedup": speedup,
            "improvement_percent": info_basic['improvement_percent']
        })
    
    if results:
        avg_terminals = sum(r['terminals'] for r in results) / len(results)
        avg_initial = sum(r['initial_len'] for r in results) / len(results)
        avg_basic_len = sum(r['basic_final_len'] for r in results) / len(results)
        avg_mod_len = sum(r['mod_final_len'] for r in results) / len(results)
        avg_basic_time = sum(r['basic_time'] for r in results) / len(results)
        avg_mod_time = sum(r['mod_time'] for r in results) / len(results)
        avg_speedup = sum(r['speedup'] for r in results) / len(results)
        avg_improvement = sum(r['improvement_percent'] for r in results) / len(results)
        avg_basic_steiners = sum(r['basic_steiners'] for r in results) / len(results)
        avg_mod_steiners = sum(r['mod_steiners'] for r in results) / len(results)
        
        print(f"{'-'*140}")
        print(f"{'AVERAGE':<8} {avg_terminals:<5.1f} {avg_initial:<6.0f} "
              f"{avg_basic_len:<8.0f} {avg_basic_time:<8.4f} "
              f"{avg_basic_steiners:<4.0f} "
              f"{avg_mod_len:<8.0f} {avg_mod_time:<8.4f} "
              f"{avg_mod_steiners:<4.0f} "
              f"{avg_speedup:<10.2f}x {avg_improvement:<6.1f}%")
        print(f"{'='*140}\n")
        
        print(f"Summary for {len(results)} tests:")
        print(f"  Average terminals per test: {avg_terminals:.1f}")
        print(f"  Average initial MST length: {avg_initial:.0f}")
        print(f"  Basic algorithm:")
        print(f"    - Average final length: {avg_basic_len:.0f}")
        print(f"    - Average time: {avg_basic_time:.4f} s")
        print(f"    - Average Steiner points: {avg_basic_steiners:.0f}")
        print(f"  Modified algorithm:")
        print(f"    - Average final length: {avg_mod_len:.0f}")
        print(f"    - Average time: {avg_mod_time:.4f} s")
        print(f"    - Average Steiner points: {avg_mod_steiners:.0f}")
        print(f"  Average speedup: {avg_speedup:.2f}x ({((avg_speedup-1)*100):.1f}% faster)")
        print(f"  Average improvement over MST: {avg_improvement:.1f}%")
        
        length_match = all(r['basic_final_len'] == r['mod_final_len'] for r in results)
        if length_match:
            print(f"  ✓ Both algorithms found the same tree length for all tests")
        else:
            diff_count = sum(1 for r in results if r['basic_final_len'] != r['mod_final_len'])
            print(f"  ⚠ Tree lengths differ in {diff_count} tests")
    
    if args.csv and results:
        import csv
        with open(args.csv, 'w', newline='') as f:
            fieldnames = ["test", "terminals", "initial_len", 
                          "basic_final_len", "basic_time", "basic_steiners",
                          "mod_final_len", "mod_time", "mod_steiners",
                          "speedup", "improvement_percent"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults saved to {args.csv}")

if __name__ == "__main__":
    main()