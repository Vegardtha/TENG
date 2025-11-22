import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re

def natural_sort_key(s):
    """Key for natural sorting of strings containing numbers"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def load_cycles(experiment_dir):
    """Load all cycle CSV files from the experiment directory"""
    pattern = os.path.join(experiment_dir, "cycle_*.csv")
    files = glob.glob(pattern)
    files.sort(key=natural_sort_key)
    
    cycles = []
    for f in files:
        try:
            # Extract cycle number from filename
            basename = os.path.basename(f)
            match = re.search(r'cycle_(\d+)\.csv', basename)
            if match:
                cycle_num = int(match.group(1))
                df = pd.read_csv(f)
                cycles.append((cycle_num, df))
        except Exception as e:
            print(f"Error loading {f}: {e}")
            
    return cycles

def plot_overlay(cycles, output_dir, title_suffix="", filename_suffix=""):
    """Plot multiple cycles overlaid on one plot"""
    if not cycles:
        print("No cycles to plot.")
        return

    plt.figure(figsize=(12, 6))
    
    for cycle_num, df in cycles:
        plt.plot(df['Timestamp_ms'], df['Voltage_V'], alpha=0.3, linewidth=0.5)
        
    plt.xlabel("Time (ms)")
    plt.ylabel("Voltage (V)")
    plt.title(f"Waveforms Overlay {title_suffix} ({len(cycles)} cycles)")
    plt.grid(alpha=0.3)
    
    filename = f"overlay_{filename_suffix}.png" if filename_suffix else "overlay.png"
    save_path = os.path.join(output_dir, filename)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Saved overlay plot: {save_path}")

def plot_chunks(cycles, output_dir, chunk_size):
    """Plot cycles in chunks"""
    # Sort cycles by cycle number just in case
    cycles.sort(key=lambda x: x[0])
    
    total_cycles = len(cycles)
    num_chunks = (total_cycles + chunk_size - 1) // chunk_size
    
    print(f"Plotting {num_chunks} chunks of size {chunk_size}...")
    
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, total_cycles)
        
        chunk_cycles = cycles[start_idx:end_idx]
        
        if not chunk_cycles:
            continue
            
        start_cycle = chunk_cycles[0][0]
        end_cycle = chunk_cycles[-1][0]
        
        title_suffix = f"- Cycles {start_cycle} to {end_cycle}"
        filename_suffix = f"cycles_{start_cycle}_{end_cycle}"
        
        plot_overlay(chunk_cycles, output_dir, title_suffix, filename_suffix)

def analyze_statistics(cycles, output_dir):
    """Perform statistical analysis on the experiment"""
    print("Analyzing statistics...")
    
    stats_data = []
    
    for cycle_num, df in cycles:
        voltage = df['Voltage_V']
        peak_voltage = np.max(np.abs(voltage))
        max_voltage = np.max(voltage)
        min_voltage = np.min(voltage)
        mean_voltage = np.mean(voltage)
        std_voltage = np.std(voltage)
        
        stats_data.append({
            'Cycle': cycle_num,
            'Peak_Voltage_V': peak_voltage,
            'Max_Voltage_V': max_voltage,
            'Min_Voltage_V': min_voltage,
            'Mean_Voltage_V': mean_voltage,
            'Std_Voltage_V': std_voltage
        })
    
    stats_df = pd.DataFrame(stats_data)
    stats_csv_path = os.path.join(output_dir, "detailed_statistics.csv")
    stats_df.to_csv(stats_csv_path, index=False)
    print(f"Saved detailed statistics to {stats_csv_path}")
    
    # Global statistics
    print("\n--- Global Statistics ---")
    print(f"Total Cycles: {len(cycles)}")
    print(f"Average Peak Voltage: {stats_df['Peak_Voltage_V'].mean():.2f} V")
    print(f"Max Peak Voltage: {stats_df['Peak_Voltage_V'].max():.2f} V (Cycle {stats_df.loc[stats_df['Peak_Voltage_V'].idxmax(), 'Cycle']})")
    print(f"Min Peak Voltage: {stats_df['Peak_Voltage_V'].min():.2f} V (Cycle {stats_df.loc[stats_df['Peak_Voltage_V'].idxmin(), 'Cycle']})")
    print(f"Std Dev of Peak Voltage: {stats_df['Peak_Voltage_V'].std():.2f} V")

    # Plot Peak Voltage Trend
    plt.figure(figsize=(12, 6))
    plt.plot(stats_df['Cycle'], stats_df['Peak_Voltage_V'], 'b-', linewidth=1, alpha=0.7)
    plt.axhline(y=stats_df['Peak_Voltage_V'].mean(), color='r', linestyle='--', label=f"Mean: {stats_df['Peak_Voltage_V'].mean():.2f} V")
    plt.xlabel("Cycle Number")
    plt.ylabel("Peak Voltage (V)")
    plt.title("Peak Voltage vs Cycle Number")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig(os.path.join(output_dir, "peak_voltage_trend.png"), dpi=150)
    plt.close()
    
    # Histogram of Peak Voltages
    plt.figure(figsize=(10, 6))
    plt.hist(stats_df['Peak_Voltage_V'], bins=30, edgecolor='black', alpha=0.7)
    plt.axvline(x=stats_df['Peak_Voltage_V'].mean(), color='r', linestyle='--', label=f"Mean: {stats_df['Peak_Voltage_V'].mean():.2f} V")
    plt.xlabel("Peak Voltage (V)")
    plt.ylabel("Count")
    plt.title("Distribution of Peak Voltages")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig(os.path.join(output_dir, "peak_voltage_distribution.png"), dpi=150)
    plt.close()

def main():
    experiment_path = "/home/troll1234/Documents/TENG/TENG/experiments/MyTest_20251121_182909"
    
    # Create a directory for plots inside the experiment folder
    plots_dir = os.path.join(experiment_path, "plots_analysis")
    os.makedirs(plots_dir, exist_ok=True)
    
    print(f"Loading data from {experiment_path}...")
    cycles = load_cycles(experiment_path)
    print(f"Loaded {len(cycles)} cycles.")
    
    if not cycles:
        print("No data found!")
        return

    # 1. Plot all overlaid
    print("\nGenerating full overlay plot...")
    plot_overlay(cycles, plots_dir, title_suffix="(All Cycles)", filename_suffix="all")
    
    # 2. Plot in chunks of 500
    print("\nGenerating 500-cycle chunk plots...")
    plot_chunks(cycles, plots_dir, chunk_size=500)
    
    # 3. Plot in chunks of 1000
    print("\nGenerating 1000-cycle chunk plots...")
    plot_chunks(cycles, plots_dir, chunk_size=1000)
    
    # 4. Statistical Analysis
    print("\nPerforming statistical analysis...")
    analyze_statistics(cycles, plots_dir)
    
    print("\nDone! Check the 'plots_analysis' folder inside the experiment directory.")

if __name__ == "__main__":
    main()
