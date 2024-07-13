import threading
import time
import random

class Process:
    def __init__(self, id, max_resources, allocated_resources):
        self.id = id
        self.max_resources = max_resources
        self.allocated_resources = allocated_resources
        self.need = [max_resources[i] - allocated_resources[i] for i in range(len(max_resources))]
        self.lock = threading.Lock()

class Resource:
    def __init__(self, total_resources):
        self.total_resources = total_resources
        self.available_resources = total_resources.copy()
        self.lock = threading.Lock()

class DynamicResource(Resource):
    def __init__(self, total_resources):
        super().__init__(total_resources)
    
    def add_resources(self, additional_resources):
        with self.lock:
            for i in range(len(self.total_resources)):
                self.total_resources[i] += additional_resources[i]
                self.available_resources[i] += additional_resources[i]

def is_safe_state(processes, available_resources):
    work = available_resources.copy()
    finish = [False] * len(processes)
    
    while True:
        found = False
        for i, process in enumerate(processes):
            if not finish[i] and all(process.need[j] <= work[j] for j in range(len(work))):
                work = [work[j] + process.allocated_resources[j] for j in range(len(work))]
                finish[i] = True
                found = True
        
        if not found:
            break
    
    return all(finish)

def request_resources(process, request, processes, resources):
    with process.lock and resources.lock:
        if any(request[i] > process.need[i] for i in range(len(request))):
            return False, "Request exceeds maximum claim"
        
        if any(request[i] > resources.available_resources[i] for i in range(len(request))):
            return False, "Resources not available"
        
        # Temporarily allocate resources
        for i in range(len(request)):
            resources.available_resources[i] -= request[i]
            process.allocated_resources[i] += request[i]
            process.need[i] -= request[i]
        
        # Check if the resulting state is safe
        if is_safe_state(processes, resources.available_resources):
            return True, "Request granted"
        else:
            # If not safe, rollback changes
            for i in range(len(request)):
                resources.available_resources[i] += request[i]
                process.allocated_resources[i] -= request[i]
                process.need[i] += request[i]
            return False, "Unsafe state"

def process_thread(process, request, processes, resources):
    success, message = request_resources(process, request, processes, resources)
    if success:
        print(f"Process {process.id} request granted. Safe sequence: {get_safe_sequence(processes, resources.available_resources)}")
    else:
        print(f"Process {process.id} request denied. {message}")

def get_safe_sequence(processes, available_resources):
    work = available_resources.copy()
    finish = [False] * len(processes)
    sequence = []
    
    while len(sequence) < len(processes):
        found = False
        for i, process in enumerate(processes):
            if not finish[i] and all(process.need[j] <= work[j] for j in range(len(work))):
                work = [work[j] + process.allocated_resources[j] for j in range(len(work))]
                finish[i] = True
                sequence.append(process.id)
                found = True
                break
        
        if not found:
            return None
    
    return sequence

def race_condition_monitor(processes, resources):
    first_check = True
    while True:
        time.sleep(1)
        with resources.lock:
            total_allocated = [sum(p.allocated_resources[i] for p in processes) for i in range(len(resources.total_resources))]
            if any(total_allocated[i] > resources.total_resources[i] for i in range(len(resources.total_resources))):
                print("Warning: Race condition detected! Allocated resources exceed total resources.")
            elif first_check:
                print("There isn't race condition anymore.")
                first_check = False
            

def display_state(processes, available_resources):
    print(f"Available Resources: {available_resources}")
    print("Processes:")
    for process in processes:
        print(f"Process {process.id}: Max: {process.max_resources}, Allocated: {process.allocated_resources}, Need: {process.need}")
    print()

def dynamic_resource_changer(resource, interval):
    while True:
        time.sleep(interval)
        additional_resources = [random.randint(0, 2) for _ in range(len(resource.total_resources))]
        resource.add_resources(additional_resources)
        print(f"Resources added: {additional_resources}")
        print(f"New total resources: {resource.total_resources}")
        print(f"New available resources: {resource.available_resources}")
        print()

def simulate_concurrent_requests(processes, resources, requests):
    threads = []
    for process, request in requests:
        thread = threading.Thread(target=process_thread, args=(process, request, processes, resources))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    available_resources = [10, 5, 7]
    resources = DynamicResource(available_resources)
    processes = [
        Process(0, [7, 5, 3], [0, 1, 0]),
        Process(1, [3, 2, 2], [2, 0, 0]),
        Process(2, [9, 0, 2], [3, 0, 2]),
        Process(3, [2, 2, 2], [2, 1, 1]),
        Process(4, [4, 3, 3], [0, 0, 2])
    ]

    display_state(processes, resources.available_resources)

    # Start race condition monitor
    monitor_thread = threading.Thread(target=race_condition_monitor, args=(processes, resources))
    monitor_thread.daemon = True
    monitor_thread.start()

    # Start dynamic resource changer
    changer_thread = threading.Thread(target=dynamic_resource_changer, args=(resources, 10))
    changer_thread.daemon = True
    changer_thread.start()

    # Simulate concurrent requests
    requests = [
        (processes[0], [0, 2, 0]),
        (processes[4], [0, 3, 0]),
        (processes[1], [1, 0, 2]),
        (processes[3], [0, 1, 0])
    ]
    
    simulate_concurrent_requests(processes, resources, requests)
    display_state(processes, resources.available_resources)

    # Manual input for additional requests
    while True:
        try:
            process_id = int(input("Enter process ID to request resources (-1 to exit): "))
            if process_id == -1:
                break
            request = list(map(int, input("Enter resource request (space-separated): ").split()))
            
            if 0 <= process_id < len(processes):
                process_thread(processes[process_id], request, processes, resources)
                display_state(processes, resources.available_resources)
            else:
                print("Invalid process ID")
        except ValueError:
            print("Invalid input. Please enter integers.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break

    print("Program finished.")