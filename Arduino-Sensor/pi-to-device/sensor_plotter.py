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

    data = {i: {'time': [], 'X': [], 'Y': [], 'Z': [], 'roll': [], 'pitch': [], 'yaw': []}
            for i in range(1, 6)}

    for block in blocks:
        lines = block.strip().split('\n')
        time_match = re.match(r'Time:\s*([\d.]+)', lines[0])
        if not time_match:
            continue
        t = float(time_match.group(1))

        # Find each sensor's data
        for sensor_id in range(1, 6):
            # Find "Sensor N:" in the block
            pattern = rf'Sensor {sensor_id}:\s*\nX:\s*([-\d.]+)\s*\|\s*Y:\s*([-\d.]+)\s*\|\s*Z:\s*([-\d.]+)\s*\nroll:\s*([-\d.]+)\s*\|\s*pitch:\s*([-\d.]+)\s*\|\s*yaw:\s*([-\d.]+)'
            m = re.search(pattern, block)
            if m:
                data[sensor_id]['time'].append(t)
                data[sensor_id]['X'].append(float(m.group(1)))
                data[sensor_id]['Y'].append(float(m.group(2)))
                data[sensor_id]['Z'].append(float(m.group(3)))
                data[sensor_id]['roll'].append(float(m.group(4)))
                data[sensor_id]['pitch'].append(float(m.group(5)))
                data[sensor_id]['yaw'].append(float(m.group(6)))

    return data


def plot_all_sensors_together(data, filename):
    """Plot all sensors on shared axes for each measurement type."""
    base = os.path.splitext(os.path.basename(filename))[0]
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']
    metrics = ['X', 'Y', 'Z', 'roll', 'pitch', 'yaw']
    metric_labels = {
        'X': 'X Accel (m/s²)', 'Y': 'Y Accel (m/s²)', 'Z': 'Z Accel (m/s²)',
        'roll': 'Roll (rad)', 'pitch': 'Pitch (rad)', 'yaw': 'Yaw (rad)'
    }

    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    fig.suptitle(f'All Sensors — {base}', fontsize=16, fontweight='bold', y=1.01)
    axes = axes.flatten()

    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        for sensor_id in range(1, 6):
            t = data[sensor_id]['time']
            v = data[sensor_id][metric]
            if t:
                ax.plot(t, v, color=colors[sensor_id - 1], label=f'Sensor {sensor_id}',
                        linewidth=1.8, marker='o', markersize=3, alpha=0.85)
        ax.set_title(metric_labels[metric], fontsize=11, fontweight='bold')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel(metric_labels[metric])
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f8f9fa')

    fig.tight_layout()
    out = f'{base}_all_sensors.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'  Saved: {out}')
    plt.show()


def plot_individual_sensors(data, filename):
    """Plot each sensor on its own figure with all 6 metrics."""
    base = os.path.splitext(os.path.basename(filename))[0]
    metrics = ['X', 'Y', 'Z', 'roll', 'pitch', 'yaw']
    metric_labels = {
        'X': 'X Accel (m/s²)', 'Y': 'Y Accel (m/s²)', 'Z': 'Z Accel (m/s²)',
        'roll': 'Roll (rad)', 'pitch': 'Pitch (rad)', 'yaw': 'Yaw (rad)'
    }
    colors_per_metric = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']

    for sensor_id in range(1, 6):
        fig, axes = plt.subplots(3, 2, figsize=(14, 10))
        fig.suptitle(f'Sensor {sensor_id} — {base}', fontsize=15, fontweight='bold')
        axes = axes.flatten()

        t = data[sensor_id]['time']
        for idx, metric in enumerate(metrics):
            ax = axes[idx]
            v = data[sensor_id][metric]
            ax.plot(t, v, color=colors_per_metric[idx], linewidth=2,
                    marker='o', markersize=4, label=metric)
            ax.set_title(metric_labels[metric], fontsize=11, fontweight='bold')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(metric_labels[metric])
            ax.grid(True, alpha=0.3)
            ax.set_facecolor('#f8f9fa')

            # Annotate min/max
            if v:
                min_i, max_i = np.argmin(v), np.argmax(v)
                ax.annotate(f'{v[min_i]:.2f}', xy=(t[min_i], v[min_i]),
                            fontsize=7, color='navy', ha='center', va='top')
                ax.annotate(f'{v[max_i]:.2f}', xy=(t[max_i], v[max_i]),
                            fontsize=7, color='darkred', ha='center', va='bottom')

        fig.tight_layout()
        out = f'{base}_sensor_{sensor_id}.png'
        plt.savefig(out, dpi=150, bbox_inches='tight')
        print(f'  Saved: {out}')
        plt.show()


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

    total = sum(len(data[s]['time']) for s in data)
    print(f'  Loaded {total} sensor readings across {len(data[1]["time"])} time steps.')

    print('\nGenerating combined plot (all sensors)...')
    plot_all_sensors_together(data, filename)

    print('\nGenerating individual sensor plots...')
    plot_individual_sensors(data, filename)

    print('\nDone!')


if __name__ == '__main__':
    main()
