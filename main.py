import pygame
import sys
import math
import random
from collections import deque
from PIL import Image # Added for GIF saving

# --- Configuration ---
WIDTH, HEIGHT = 900, 700
FPS = 60
BG_COLOR = (240, 245, 240)
ROAD_COLOR = (180, 180, 180)
LINE_COLOR = (255, 255, 255)

# --- GIF Recording Configuration ---
RECORD_GIF = True
GIF_DURATION_SEC = 10
GIF_FPS = 30 # 30 FPS keeps file size manageable while staying smooth
FRAMES_TO_CAPTURE = GIF_DURATION_SEC * GIF_FPS
CAPTURE_INTERVAL = max(1, FPS // GIF_FPS) 

# --- Network Definition ---
NODES = {
    'S14': (100, 150), 'J1': (350, 150), 'J2': (550, 150), 'K2': (800, 150),
    'S25': (100, 350), 'J3': (350, 350), 'J4': (550, 350), 'S3': (800, 350),
    'K34': (100, 550), 'J5': (350, 550), 'J6': (550, 550), 'K15': (800, 550)
}

EDGES_LIST = [
    ('S14', 'J1'), ('J1', 'S14'), ('J1', 'J2'), ('J2', 'J1'), ('J2', 'K2'), ('K2', 'J2'),
    ('S25', 'J3'), ('J3', 'S25'), ('J3', 'J4'), ('J4', 'J3'), ('J4', 'S3'), ('S3', 'J4'),
    ('K34', 'J5'), ('J5', 'K34'), ('J5', 'J6'), ('J6', 'J5'), ('J6', 'K15'), ('K15', 'J6'),
    ('J1', 'J3'), ('J3', 'J1'), ('J3', 'J5'), ('J5', 'J3'),
    ('J2', 'J4'), ('J4', 'J2'), ('J4', 'J6'), ('J6', 'J4')
]

SOURCES = ['S14', 'S25', 'S3']
SINKS = ['K2', 'K34', 'K15']

# --- Helper Functions ---
def get_distance(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def get_offset_points(start_node, end_node, offset=6):
    p1, p2 = NODES[start_node], NODES[end_node]
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0: return p1, p2
    nx, ny = -dy / length, dx / length 
    return (p1[0] + nx * offset, p1[1] + ny * offset), (p2[0] + nx * offset, p2[1] + ny * offset)

def build_paths():
    adj = {n: [] for n in NODES}
    for u, v in EDGES_LIST:
        adj[u].append(v)
    
    paths = {}
    for src in SOURCES:
        paths[src] = {}
        for snk in SINKS:
            queue = deque([(src, [src])])
            visited = set([src])
            found_path = None
            while queue:
                curr, path = queue.popleft()
                if curr == snk:
                    found_path = path
                    break
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))
            paths[src][snk] = found_path
    return paths

PATHS = build_paths()

# --- Simulation Classes ---
class Vehicle:
    def __init__(self, path):
        self.path = path
        self.path_index = 0
        self.current_edge = (path[0], path[1])
        self.progress = 0.0  
        self.max_speed = random.uniform(1.5, 2.5)
        self.speed = self.max_speed
        self.color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
        self.length = 10
        self.safe_distance = 15

    def move(self, edge_vehicles, junctions_occupied):
        p1, p2 = NODES[self.current_edge[0]], NODES[self.current_edge[1]]
        edge_length = get_distance(p1, p2)
        
        vehicles_on_my_edge = edge_vehicles.get(self.current_edge, [])
        my_idx = vehicles_on_my_edge.index(self)
        
        target_speed = self.max_speed
        if my_idx > 0:
            veh_ahead = vehicles_on_my_edge[my_idx - 1]
            distance_ahead = (veh_ahead.progress - self.progress)
            if distance_ahead < self.safe_distance:
                target_speed = veh_ahead.speed * 0.8  
                if distance_ahead < self.length:
                    target_speed = 0 
                    
        distance_to_end = edge_length - self.progress
        if distance_to_end < self.safe_distance and self.path_index + 2 < len(self.path):
            next_node = self.path[self.path_index + 1]
            if junctions_occupied.get(next_node, False):
                target_speed = 0

        if self.speed < target_speed:
            self.speed = min(self.speed + 0.1, target_speed)
        else:
            self.speed = max(self.speed - 0.2, target_speed)

        self.progress += self.speed
        
        if self.progress >= edge_length:
            self.path_index += 1
            if self.path_index >= len(self.path) - 1:
                return True 
            
            self.current_edge = (self.path[self.path_index], self.path[self.path_index+1])
            self.progress = 0.0
            
        return False 

    def draw(self, surface):
        p1, p2 = get_offset_points(self.current_edge[0], self.current_edge[1])
        edge_len = get_distance(p1, p2)
        if edge_len == 0: return
        
        ratio = self.progress / edge_len
        ratio = max(0, min(1, ratio)) 
        
        x = p1[0] + (p2[0] - p1[0]) * ratio
        y = p1[1] + (p2[1] - p1[1]) * ratio
        
        pygame.draw.circle(surface, self.color, (int(x), int(y)), 5)

# --- Main Game Loop ---
def main():
    global RECORD_GIF
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Network Traffic Simulator - Assignment 6")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    vehicles = []
    spawn_rate = 30 
    frame_count = 0
    total_frames = 0
    captured_images = []
    
    running = True
    while running:
        screen.fill(BG_COLOR)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:   
                    spawn_rate = max(5, spawn_rate - 5)
                elif event.key == pygame.K_DOWN: 
                    spawn_rate = min(120, spawn_rate + 5)

        # 1. Spawning Logic
        frame_count += 1
        if frame_count >= spawn_rate:
            frame_count = 0
            src = random.choice(SOURCES)
            snk = random.choice(SINKS)
            path = PATHS[src].get(snk)
            if path:
                first_edge = (path[0], path[1])
                clear_to_spawn = True
                for v in vehicles:
                    if v.current_edge == first_edge and v.progress < 20:
                        clear_to_spawn = False
                        break
                if clear_to_spawn:
                    vehicles.append(Vehicle(path))

        # 2. State Mapping
        edge_vehicles = {edge: [] for edge in EDGES_LIST}
        for v in vehicles:
            edge_vehicles[v.current_edge].append(v)
            
        for edge in edge_vehicles:
            edge_vehicles[edge].sort(key=lambda x: x.progress, reverse=True)

        junctions_occupied = {}
        for v in vehicles:
            if v.progress < 15:
                junctions_occupied[v.current_edge[0]] = True

        # 3. Update Vehicles
        active_vehicles = []
        for v in vehicles:
            arrived = v.move(edge_vehicles, junctions_occupied)
            if not arrived:
                active_vehicles.append(v)
        vehicles = active_vehicles

        # 4. Drawing Phase
        for u, v in EDGES_LIST:
            p1, p2 = get_offset_points(u, v)
            pygame.draw.line(screen, ROAD_COLOR, p1, p2, 10)
            
        for name, pos in NODES.items():
            color = (100, 200, 100) if name in SOURCES else (200, 100, 100) if name in SINKS else (200, 200, 200)
            pygame.draw.circle(screen, color, pos, 15)
            label = font.render(name, True, (0, 0, 0))
            screen.blit(label, (pos[0] - 10, pos[1] - 25))

        for v in vehicles:
            v.draw(screen)

        # UI Stats Overlay
        intensity_text = font.render(f"Traffic Intensity: {1000//spawn_rate} veh/sec limit", True, (0,0,0))
        active_text = font.render(f"Active Vehicles: {len(vehicles)}", True, (0,0,0))
        screen.blit(intensity_text, (10, 10))
        screen.blit(active_text, (10, 35))

        # --- GIF Capture Logic ---
        if RECORD_GIF:
            # Draw recording indicator
            rec_text = font.render(f"RECORDING... ({len(captured_images)}/{FRAMES_TO_CAPTURE})", True, (255, 0, 0))
            screen.blit(rec_text, (WIDTH - 250, 10))
            
            if total_frames % CAPTURE_INTERVAL == 0:
                raw_str = pygame.image.tobytes(screen, 'RGB')
                img = Image.frombytes('RGB', (WIDTH, HEIGHT), raw_str)
                captured_images.append(img)
                
            if len(captured_images) >= FRAMES_TO_CAPTURE:
                RECORD_GIF = False
                print("\nSaving GIF... Please wait, this may take a moment.")
                
                # Render a "Saving..." text before the freeze
                save_text = font.render("SAVING GIF TO FOLDER...", True, (255, 0, 0))
                screen.blit(save_text, (WIDTH // 2 - 100, HEIGHT // 2))
                pygame.display.flip()
                
                captured_images[0].save(
                    'traffic_simulation.gif',
                    save_all=True,
                    append_images=captured_images[1:],
                    optimize=True,
                    duration=1000 // GIF_FPS,
                    loop=0
                )
                print("Success! Saved as 'traffic_simulation.gif'.")

        total_frames += 1

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()