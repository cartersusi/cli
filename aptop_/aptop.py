from re import compile
from colorama import Fore, Back, Style, init
from asyncio import subprocess, CancelledError, create_subprocess_exec, wait_for, all_tasks, get_event_loop
from argparse import ArgumentParser
from signal import signal, SIGINT
from warnings import filterwarnings
from time import sleep
filterwarnings("ignore", category=DeprecationWarning)
init(autoreset=True)

PATTERNS = {
    'gpu_usage': compile(r'GPU HW active residency:\s+([\d.]+)%'),
    'gpu_freq': compile(r'GPU HW active frequency:\s+([\d.]+)\s+MHz'),
    'gpu_power': compile(r'GPU Power:\s+([\d.]+)\s+mW'),
    'p_cpu_usage': compile(r'P-Cluster idle residency:\s+([\d.]+)'),
    'e_cpu_usage': compile(r'E-Cluster idle residency:\s+([\d.]+)'),
    'cpu_freq_e': compile(r'E-Cluster HW active frequency:\s+([\d.]+)\s+MHz'),
    'cpu_freq_p': compile(r'P-Cluster HW active frequency:\s+([\d.]+)\s+MHz'),
    'cpu_power': compile(r'CPU Power:\s+([\d.]+)\s+mW'),
    'total_power': compile(r'Combined Power \(CPU \+ GPU \+ ANE\):\s+([\d.]+)\s+mW'),
    'network_out': compile(r'out:.*\s+([\d.]+)\s+bytes/s'),
    'network_in': compile(r'in:.*\s+([\d.]+)\s+bytes/s'),
    'disk_read': compile(r'read:.*\s+([\d.]+)\s+KBytes/s'),
    'disk_write': compile(r'write:.*\s+([\d.]+)\s+KBytes/s')
}

def parse_metrics(output):
    metrics = {}
    for key, pattern in PATTERNS.items():
        match = pattern.search(output)
        metrics[key] = float(match.group(1)) if match else 0
    
    metrics['cpu_usage_e'] = 100 - metrics['e_cpu_usage']
    metrics['cpu_usage_p'] = 100 - metrics['p_cpu_usage']
    metrics['cpu_usage'] = (metrics['cpu_usage_e'] + metrics['cpu_usage_p']) / 2
    
    return metrics

def color_value(value, low, medium):
    if value < low:
        return f"{Fore.GREEN}{value:.2f}{Style.RESET_ALL}"
    elif value < medium:
        return f"{Fore.YELLOW}{value:.2f}{Style.RESET_ALL}"
    else:
        return f"{Fore.RED}{value:.2f}{Style.RESET_ALL}"

def format_bar(value, max_value, width=20):
    filled_width = int(value / max_value * width)
    bar = '█' * filled_width + '░' * (width - filled_width)
    return f"{Fore.CYAN}{bar}{Style.RESET_ALL}"

def display_metrics(metrics):
    clear_screen = "\033[2J\033[H"
    
    output = f"{Back.BLUE}{Fore.WHITE}{'System Metrics':^40}{Style.RESET_ALL}\n\n"
    
    sections = [
        ("GPU Metrics", [
            (f"Usage: {color_value(metrics['gpu_usage'], 30, 70)}% {format_bar(metrics['gpu_usage'], 100)}",),
            (f"Frequency: {metrics['gpu_freq']:.2f} MHz",),
            (f"Power: {color_value(metrics['gpu_power'], 1000, 3000)} mW",)
        ]),
        ("CPU Metrics", [
            (f"Usage: {color_value(metrics['cpu_usage'], 30, 70)}% {format_bar(metrics['cpu_usage'], 100)}",),
            (f"E-Cluster: {metrics['cpu_freq_e']:.2f} MHz, {color_value(metrics['cpu_usage_e'], 30, 70)}%",),
            (f"P-Cluster: {metrics['cpu_freq_p']:.2f} MHz, {color_value(metrics['cpu_usage_p'], 30, 70)}%",),
            (f"Power: {color_value(metrics['cpu_power'], 1000, 3000)} mW",)
        ]),
        ("Power", [
            (f"Total: {color_value(metrics['total_power'], 2000, 5000)} mW",)
        ]),
        ("Network", [
            (f"Out: {metrics['network_out']:.2f} bytes/s",),
            (f"In: {metrics['network_in']:.2f} bytes/s",)
        ]),
        ("Disk", [
            (f"Read: {metrics['disk_read']:.2f} KB/s",),
            (f"Write: {metrics['disk_write']:.2f} KB/s",)
        ])
    ]
    
    for title, items in sections:
        output += f"{Fore.MAGENTA}{title}:{Style.RESET_ALL}\n"
        output += "\n".join(item[0] for item in items) + "\n\n"
    
    print(f"{clear_screen}{output}", end="", flush=True)
    print(f"{clear_screen}{output}", end="", flush=True)


async def read_output(process):
    output_buffer = []
    while True:
        output = await process.stdout.readline()
        if not output:
            sleep(0.1)
            break
        output_buffer.append(output.decode())
        if "Combined Power (CPU + GPU + ANE):" in output.decode():
            yield ''.join(output_buffer)
            output_buffer.clear()

async def main(interval):
    process = None
    try:
        process = await create_subprocess_exec(
            "powermetrics", "-i", str(interval),
            stdout=subprocess.PIPE
        )
        async for output in read_output(process):
            metrics = parse_metrics(output)
            display_metrics(metrics)
    except CancelledError:
        pass
    finally:
        if process and process.returncode is None:
            try:
                process.terminate()
                await wait_for(process.wait(), timeout=2.0)
            except TimeoutError:
                process.kill()

def signal_handler(signum, frame):
    for task in all_tasks():
        task.cancel()

if __name__ == "__main__":
    parser = ArgumentParser(description="Monitor system metrics")
    parser.add_argument("-i", "--interval", type=int, default=1000,
                        help="Update interval in milliseconds")
    args = parser.parse_args()

    loop = get_event_loop()
    main_task = loop.create_task(main(args.interval))
    signal(SIGINT, signal_handler)

    try:
        loop.run_until_complete(main_task)
    except CancelledError:
        pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        print("Monitoring stopped.")

def custom_exception_handler(loop, context):
    if "exception" in context:
        if not isinstance(context["exception"], RuntimeError) or \
           "Event loop is closed" not in str(context["exception"]):
            loop.default_exception_handler(context)

get_event_loop().set_exception_handler(custom_exception_handler)