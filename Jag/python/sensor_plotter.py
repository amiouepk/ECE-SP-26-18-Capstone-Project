import re
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import sys
import os

def parse_sensor_file(filename):
    """Parse sensor data text file and return structured data."""
    with open(filename, 'r') as f:
        content = f.read()

    # Split into time blocks
    blocks = re.split(r'(?=Time:\s)', content.strip())
    blocks = [b.strip() for b in blocks if b.strip()]

    # Initialize data dict for 6 sensors (1 to 6)
    data = {i: {'time': [], 'X': [], 'Y': [], 'Z': [], 
                'gyro_x': [], 'gyro_y': [], 'gyro_z': [],
                'mag_x': [], 'mag_y': [], 'mag_z': []}
            for i in range(1, 7)}

    for block in blocks:
        lines = block.strip().split('\n')
        time_match = re.match(r'Time:\s*([\d.]+)', lines[0])
        if not time_match:
            continue
        t = float(time_match.group(1))

        # Find each sensor's data
        for sensor_id in range(1, 7):
            # Regex handles standard X/Y/Z + gyro, and optionally catches mag if it exists
            pattern = rf'Sensor {sensor_id}:\s*\nX:\s*([-\d.]+)\s*\|\s*Y:\s*([-\d.]+)\s*\|\s*Z:\s*([-\d.]+)\s*\ngyro_x:\s*([-\d.]+)\s*\|\s*gyro_y:\s*([-\d.]+)\s*\|\s*gyro_z:\s*([-\d.]+)(?:\s*\nmag_x:\s*([-\d.]+)\s*\|\s*mag_y:\s*([-\d.]+)\s*\|\s*mag_z:\s*([-\d.]+))?'
            m = re.search(pattern, block)
            
            if m:
                data[sensor_id]['time'].append(t)
                data[sensor_id]['X'].append(float(m.group(1)))
                data[sensor_id]['Y'].append(float(m.group(2)))
                data[sensor_id]['Z'].append(float(m.group(3)))
                data[sensor_id]['gyro_x'].append(float(m.group(4)))
                data[sensor_id]['gyro_y'].append(float(m.group(5)))
                data[sensor_id]['gyro_z'].append(float(m.group(6)))
                
                # Handle optional magnetometer data (Only on Sensor 1 currently)
                if m.group(7):
                    data[sensor_id]['mag_x'].append(float(m.group(7)))
                    data[sensor_id]['mag_y'].append(float(m.group(8)))
                    data[sensor_id]['mag_z'].append(float(m.group(9)))
                else:
                    data[sensor_id]['mag_x'].append(np.nan)
                    data[sensor_id]['mag_y'].append(np.nan)
                    data[sensor_id]['mag_z'].append(np.nan)

    return data


def plot_all_sensors_together(data, filename):
    """Plot all sensors on shared axes for each measurement type."""
    base = os.path.splitext(os.path.basename(filename))[0]
    
    # 6 colors for 6 sensors
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
    metrics = ['X', 'Y', 'Z', 'gyro_x', 'gyro_y', 'gyro_z', 'mag_x', 'mag_y', 'mag_z']
    metric_labels = {
        'X': 'X Accel', 'Y': 'Y Accel', 'Z': 'Z Accel',
        'gyro_x': 'Gyro X', 'gyro_y': 'Gyro Y', 'gyro_z': 'Gyro Z',
        'mag_x': 'Mag X', 'mag_y': 'Mag Y', 'mag_z': 'Mag Z'
    }

    # 3x3 Grid for 9 metrics
    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    fig.suptitle(f'All Sensors — {base}', fontsize=16, fontweight='bold', y=1.01)
    axes = axes.flatten()

    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        for sensor_id in range(1, 7):
            t = data[sensor_id]['time']
            v = data[sensor_id][metric]
            
            # Check if this sensor actually has data for this metric (skip if all NaNs)
            if t and not all(np.isnan(val) for val in v):
                ax.plot(t, v, color=colors[sensor_id - 1], label=f'Sensor {sensor_id}',
                        linewidth=1.8, marker='o', markersize=3, alpha=0.85)
                
        ax.set_title(metric_labels[metric], fontsize=11, fontweight='bold')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel(metric_labels[metric])
        
        # Only show legend if there's actually data plotted
        if ax.get_legend_handles_labels()[0]:
            ax.legend(loc='upper right', fontsize=8)
            
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f8f9fa')

    fig.tight_layout()
    out = f'{base}_all_sensors.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'  Saved: {out}')
    # plt.show()


def plot_individual_sensors(data, filename):
    """Plot each sensor on its own figure with all metrics."""
    base = os.path.splitext(os.path.basename(filename))[0]
    metrics = ['X', 'Y', 'Z', 'gyro_x', 'gyro_y', 'gyro_z', 'mag_x', 'mag_y', 'mag_z']
    metric_labels = {
        'X': 'X Accel', 'Y': 'Y Accel', 'Z': 'Z Accel',
        'gyro_x': 'Gyro X', 'gyro_y': 'Gyro Y', 'gyro_z': 'Gyro Z',
        'mag_x': 'Mag X', 'mag_y': 'Mag Y', 'mag_z': 'Mag Z'
    }
    
    # 9 colors for the 9 subplots
    colors_per_metric = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e', '#7f8c8d']

    for sensor_id in range(1, 7):
        # Skip if sensor has no data completely
        if not data[sensor_id]['time']:
            continue

        fig, axes = plt.subplots(3, 3, figsize=(18, 12))
        fig.suptitle(f'Sensor {sensor_id} — {base}', fontsize=15, fontweight='bold')
        axes = axes.flatten()

        t = data[sensor_id]['time']
        for idx, metric in enumerate(metrics):
            ax = axes[idx]
            v = data[sensor_id][metric]
            
            ax.set_title(metric_labels[metric], fontsize=11, fontweight='bold')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(metric_labels[metric])
            ax.grid(True, alpha=0.3)
            ax.set_facecolor('#f8f9fa')

            # Filter out NaNs for plotting and min/max logic
            valid_data = [(t_val, v_val) for t_val, v_val in zip(t, v) if not np.isnan(v_val)]
            
            if valid_data:
                t_valid, v_valid = zip(*valid_data)
                ax.plot(t_valid, v_valid, color=colors_per_metric[idx], linewidth=2,
                        marker='o', markersize=4, label=metric)
                        
                # Annotate min/max securely
                min_i, max_i = np.argmin(v_valid), np.argmax(v_valid)
                ax.annotate(f'{v_valid[min_i]:.2f}', xy=(t_valid[min_i], v_valid[min_i]),
                            fontsize=7, color='navy', ha='center', va='top')
                ax.annotate(f'{v_valid[max_i]:.2f}', xy=(t_valid[max_i], v_valid[max_i]),
                            fontsize=7, color='darkred', ha='center', va='bottom')
            else:
                # Add a watermark if this specific sensor is missing this specific metric
                ax.text(0.5, 0.5, 'No Data', ha='center', va='center', 
                        transform=ax.transAxes, color='gray', fontsize=12, fontstyle='italic')

        fig.tight_layout()
        out = f'{base}_sensor_{sensor_id}.png'
        plt.savefig(out, dpi=150, bbox_inches='tight')
        print(f'  Saved: {out}')
        # plt.show()


def main():
    if len(sys.argv) < 2:
        filename = input('Enter the sensor data filename (e.g. fist.txt): ').strip()
    else:
        filename = sys.argv[1]

    if not os.path.exists(filename):
        print(f'Error: File "{filename}" not found.')
        sys.exit(1)

    print(f'\nParsing: {filename}')
    data = parse_sensor_file(filename)

    total_readings = sum(len(data[s]['time']) for s in data)
    steps = len(data[1]['time']) if data[1]['time'] else 0
    print(f'  Loaded {total_readings} sensor readings across {steps} time steps.')

    print('\nGenerating combined plot (all sensors)...')
    plot_all_sensors_together(data, filename)

    # Uncomment this if you want it to automatically run the individual generation!
    # print('\nGenerating individual sensor plots...')
    # plot_individual_sensors(data, filename)

    print('\nDone!')


if __name__ == '__main__':
    main()