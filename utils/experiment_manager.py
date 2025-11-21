"""
TENG Experiment Manager
Main experiment class that coordinates motor and oscilloscope
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from .dwfconstants import trigcondRisingPositive, trigcondFallingNegative

from hardware import MotorController, OscilloscopeController


class TENGExperiment:
    """
    Manages complete TENG experiment: motor control + oscilloscope acquisition
    """
    
    def __init__(self, config):
        """Initialize experiment with configuration"""
        self.config = config
        self.motor = None
        self.oscilloscope = None
        self.output_dir = None
        self.results = []
        
    def setup(self):
        """Initialize hardware connections and create output directory"""
        print("\n" + "="*70)
        print("TENG EXPERIMENT SETUP")
        print("="*70)
        
        # Create output directory
        self.output_dir = self.config.get_output_directory()
        print(f"\n✓ Output directory: {self.output_dir}")
        
        # Save configuration
        self.config.save_config_to_file(self.output_dir)
        
        # Initialize motor controller
        print("\n--- Motor Controller ---")
        self.motor = MotorController(
            port=self.config.motor.port,
            baudrate=self.config.motor.baudrate
        )
        self.motor.connect()
        
        # Initialize oscilloscope
        print("\n--- Oscilloscope ---")
        self.oscilloscope = OscilloscopeController()
        self.oscilloscope.connect()
        
        # Configure oscilloscope
        self.oscilloscope.configure(
            sampling_frequency=self.config.oscilloscope.sampling_frequency,
            offset=self.config.oscilloscope.offset,
            amplitude_range=self.config.oscilloscope.amplitude_range,
            channel=self.config.oscilloscope.channel
        )
        
        # Setup trigger
        trigger_condition = (trigcondRisingPositive if self.config.oscilloscope.trigger_edge == "rising" 
                           else trigcondFallingNegative)
        self.oscilloscope.setup_trigger(
            trigger_channel=self.config.oscilloscope.trigger_channel,
            trigger_level=self.config.oscilloscope.trigger_level,
            trigger_condition=trigger_condition
        )
        
        # Configure acquisition time
        self.num_samples = self.oscilloscope.configure_acquisition_time(
            self.config.oscilloscope.acquisition_time_ms,
            self.config.oscilloscope.sampling_frequency
        )
        
        print(f"\n✓ Setup complete - Ready for {self.config.motor.num_cycles} cycles")
        print("="*70 + "\n")
        
    def run_single_acquisition(self, cycle_num):
        """Run a single data acquisition (called after each motor cycle)"""
        print(f"\n  → Acquiring data (cycle {cycle_num})...")
        
        # Acquire voltage data
        voltage_data = self.oscilloscope.acquire_single(
            self.num_samples,
            channel=self.config.oscilloscope.channel
        )
        
        # Create timestamp array
        timestamp = self.oscilloscope.create_timestamp_array(
            self.num_samples,
            self.config.oscilloscope.sampling_frequency
        )
        
        # Create DataFrame
        df = pd.DataFrame({
            'Timestamp_ms': timestamp,
            'Voltage_V': voltage_data
        })
        
        # Calculate peak voltage
        peak_voltage = np.max(np.abs(voltage_data))
        print(f"  ✓ Data acquired - Peak voltage: {peak_voltage:.2f} V")
        
        # Save data
        csv_path = f"{self.output_dir}/cycle_{cycle_num:03d}.csv"
        df.to_csv(csv_path, index=False)
        print(f"  ✓ Saved: {csv_path}")
        
        # Store result
        self.results.append({
            'cycle': cycle_num,
            'timestamp': datetime.now(),
            'peak_voltage': peak_voltage,
            'data': df
        })
        
        # Plot if enabled
        if self.config.plot_during_acquisition:
            self._plot_waveform(df, cycle_num, peak_voltage)
            
        return df
    
    def _plot_waveform(self, df, cycle_num, peak_voltage):
        """Plot waveform for a single acquisition"""
        plt.figure(figsize=(10, 5))
        plt.plot(df['Timestamp_ms'], df['Voltage_V'], linewidth=0.8)
        plt.axhline(y=self.config.oscilloscope.trigger_level, 
                   color='r', linestyle='--', label='Trigger Level', alpha=0.7)
        plt.xlabel("Time (ms)")
        plt.ylabel("Voltage (V)")
        plt.title(f"Cycle {cycle_num} - Peak: {peak_voltage:.2f} V")
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        
        if self.config.save_plots:
            plot_path = f"{self.output_dir}/cycle_{cycle_num:03d}.png"
            plt.savefig(plot_path, dpi=150)
            plt.close()
        else:
            plt.show()
    
    def run(self):
        """Execute complete experiment"""
        try:
            # Setup hardware
            self.setup()
            
            # Run experiment cycles with synchronized acquisition
            def acquisition_callback(cycle_num):
                self.run_single_acquisition(cycle_num)
            
            self.motor.run_experiment_cycles(
                num_cycles=self.config.motor.num_cycles,
                cycle_callback=acquisition_callback,
                cycle_delay=self.config.motor.cycle_delay
            )
            
            # Generate summary
            self._generate_summary()
            
        except KeyboardInterrupt:
            print("\n\n⚠ Experiment interrupted by user")
            
        except Exception as e:
            print(f"\n\n✗ Error during experiment: {e}")
            raise
            
        finally:
            self.cleanup()
    
    def _generate_summary(self):
        """Generate experiment summary with statistics and plots"""
        print("\n" + "="*70)
        print("GENERATING EXPERIMENT SUMMARY")
        print("="*70)
        
        if not self.results:
            print("⚠ No data collected")
            return
        
        # Extract statistics
        cycles = [r['cycle'] for r in self.results]
        peak_voltages = [r['peak_voltage'] for r in self.results]
        
        # Summary statistics
        summary_df = pd.DataFrame({
            'Cycle': cycles,
            'Peak_Voltage_V': peak_voltages
        })
        
        summary_path = f"{self.output_dir}/experiment_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        print(f"\n✓ Summary saved: {summary_path}")
        
        # Statistics
        print("\n--- Statistics ---")
        print(f"Total Cycles: {len(cycles)}")
        print(f"Mean Peak Voltage: {np.mean(peak_voltages):.2f} V")
        print(f"Std Dev: {np.std(peak_voltages):.2f} V")
        print(f"Max Peak: {np.max(peak_voltages):.2f} V")
        print(f"Min Peak: {np.min(peak_voltages):.2f} V")
        
        # Generate summary plots
        if self.config.save_plots:
            self._plot_summary(cycles, peak_voltages)
    
    def _plot_summary(self, cycles, peak_voltages):
        """Generate summary plots"""
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # Peak voltage over cycles
        axes[0].plot(cycles, peak_voltages, 'o-', linewidth=2, markersize=6)
        axes[0].axhline(y=np.mean(peak_voltages), color='r', linestyle='--', 
                       label=f'Mean: {np.mean(peak_voltages):.2f} V', alpha=0.7)
        axes[0].set_xlabel("Cycle Number")
        axes[0].set_ylabel("Peak Voltage (V)")
        axes[0].set_title("Peak Voltage vs Cycle Number")
        axes[0].legend()
        axes[0].grid(alpha=0.3)
        
        # Histogram
        axes[1].hist(peak_voltages, bins=20, edgecolor='black', alpha=0.7)
        axes[1].axvline(x=np.mean(peak_voltages), color='r', linestyle='--', 
                       label=f'Mean: {np.mean(peak_voltages):.2f} V', linewidth=2)
        axes[1].set_xlabel("Peak Voltage (V)")
        axes[1].set_ylabel("Frequency")
        axes[1].set_title("Peak Voltage Distribution")
        axes[1].legend()
        axes[1].grid(alpha=0.3, axis='y')
        
        plt.tight_layout()
        summary_plot_path = f"{self.output_dir}/experiment_summary.png"
        plt.savefig(summary_plot_path, dpi=150)
        plt.close()
        print(f"✓ Summary plots saved: {summary_plot_path}")
        
        # Overlay plot of all waveforms
        self._plot_all_waveforms_overlay()
    
    def _plot_all_waveforms_overlay(self):
        """Create overlay plot of all acquired waveforms"""
        plt.figure(figsize=(12, 6))
        
        for result in self.results:
            df = result['data']
            cycle = result['cycle']
            plt.plot(df['Timestamp_ms'], df['Voltage_V'], 
                    alpha=0.6, linewidth=0.8, label=f"Cycle {cycle}")
        
        plt.xlabel("Time (ms)")
        plt.ylabel("Voltage (V)")
        plt.title(f"All Waveforms Overlay - {len(self.results)} Cycles")
        plt.grid(alpha=0.3)
        
        # Only show legend if not too many cycles
        if len(self.results) <= 10:
            plt.legend(loc='best', fontsize=8)
        
        plt.tight_layout()
        overlay_path = f"{self.output_dir}/all_waveforms_overlay.png"
        plt.savefig(overlay_path, dpi=150)
        plt.close()
        print(f"✓ Overlay plot saved: {overlay_path}")
    
    def cleanup(self):
        """Disconnect hardware"""
        print("\n" + "="*70)
        print("CLEANUP")
        print("="*70)
        
        if self.motor:
            self.motor.disconnect()
        if self.oscilloscope:
            self.oscilloscope.disconnect()
            
        print("✓ Experiment complete\n")
