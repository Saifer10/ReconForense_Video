#!/usr/bin/env python3

import os
import json
import html
import hashlib
import subprocess
import threading
import queue
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import cv2
import numpy as np
from PIL import Image, ImageTk


# ============================================================
# CONFIGURACION
# ============================================================

APP_NAME = "HIDRA ACADEMY - VIDEO FORENSICS LAB"

BASE_DIR = os.path.expanduser("~/VideoForensics")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# COLORES
# ============================================================

BACKGROUND = "#020607"
PANEL = "#061011"
PANEL_DARK = "#030A0B"
PANEL_BUTTON = "#071719"
PANEL_HOVER = "#0A1D20"

BORDER = "#00D9E8"
BORDER_SOFT = "#007C86"

TEXT = "#B7F7FF"
TEXT_DIM = "#7FAAB0"
TEXT_TITLE = "#E7FFFF"

SUCCESS = "#38E0B5"
WARNING = "#FFD166"
DANGER = "#FF4D4D"


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def run_command(command):

    try:

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except Exception as error:

        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(error)
        }


def safe_name(name):

    return "".join(
        character
        if character.isalnum() or character in "._-"
        else "_"
        for character in name
    )


def create_case_directory(video_path):

    video_name = os.path.basename(video_path)

    base_name = os.path.splitext(video_name)[0]

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    case_name = safe_name(
        f"{base_name}_{timestamp}"
    )

    case_dir = os.path.join(
        OUTPUT_DIR,
        case_name
    )

    os.makedirs(
        case_dir,
        exist_ok=True
    )

    return case_dir


def format_time(seconds):

    try:

        seconds = float(seconds)

        hours = int(seconds // 3600)

        minutes = int(
            (seconds % 3600) // 60
        )

        seconds = seconds % 60

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:06.3f}"
        )

    except Exception:

        return "N/A"


# ============================================================
# HASH
# ============================================================

def generate_hashes(video_path, case_dir):

    algorithms = [
        "md5",
        "sha1",
        "sha256",
        "sha512"
    ]

    results = {}

    for algorithm in algorithms:

        hasher = hashlib.new(algorithm)

        with open(
            video_path,
            "rb"
        ) as file:

            while True:

                block = file.read(
                    1024 * 1024
                )

                if not block:

                    break

                hasher.update(block)

        results[
            algorithm.upper()
        ] = hasher.hexdigest()


    output_file = os.path.join(
        case_dir,
        "hashes.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=4
        )

    return results


# ============================================================
# METADATOS
# ============================================================

def extract_metadata(video_path, case_dir):

    output_file = os.path.join(
        case_dir,
        "metadata.txt"
    )

    result = run_command([

        "exiftool",

        "-G1",

        "-a",

        "-s",

        video_path

    ])

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            result["stdout"]
        )

        if result["stderr"]:

            file.write(
                "\n\n--- STDERR ---\n"
            )

            file.write(
                result["stderr"]
            )

    return output_file


# ============================================================
# INFORMACION DEL VIDEO
# ============================================================

def get_video_info(video_path):

    capture = cv2.VideoCapture(
        video_path
    )

    if not capture.isOpened():

        raise RuntimeError(
            "No fue posible abrir el video."
        )

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    frames = int(
        capture.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    width = int(
        capture.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )
    )

    height = int(
        capture.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )
    )

    duration = (
        frames / fps
        if fps > 0
        else 0
    )

    capture.release()

    return {

        "fps": fps,

        "frames": frames,

        "width": width,

        "height": height,

        "duration": duration

    }


# ============================================================
# EXTRAER FRAMES
# ============================================================

def extract_frames(video_path, case_dir):

    frames_dir = os.path.join(
        case_dir,
        "frames"
    )

    os.makedirs(
        frames_dir,
        exist_ok=True
    )

    command = [

        "ffmpeg",

        "-y",

        "-i",

        video_path,

        "-vsync",

        "0",

        os.path.join(
            frames_dir,
            "frame_%08d.png"
        )

    ]

    result = run_command(
        command
    )

    if result["returncode"] != 0:

        raise RuntimeError(
            result["stderr"]
        )

    total = len([
        file
        for file in os.listdir(frames_dir)
        if file.endswith(".png")
    ])

    return frames_dir, total


# ============================================================
# DIFERENCIA ENTRE FRAMES
# ============================================================

def frame_difference(frame1, frame2):

    gray1 = cv2.cvtColor(
        frame1,
        cv2.COLOR_BGR2GRAY
    )

    gray2 = cv2.cvtColor(
        frame2,
        cv2.COLOR_BGR2GRAY
    )

    difference = cv2.absdiff(
        gray1,
        gray2
    )

    return float(
        np.mean(difference)
    )


# ============================================================
# FRAMES DUPLICADOS
# ============================================================

def detect_duplicate_frames(
    video_path,
    case_dir,
    threshold=1.5
):

    capture = cv2.VideoCapture(
        video_path
    )

    duplicates = []

    previous_frame = None

    frame_number = 0

    while True:

        success, frame = capture.read()

        if not success:

            break

        if previous_frame is not None:

            small_current = cv2.resize(
                frame,
                (320, 180)
            )

            small_previous = cv2.resize(
                previous_frame,
                (320, 180)
            )

            score = frame_difference(
                small_previous,
                small_current
            )

            if score <= threshold:

                duplicates.append({

                    "frame": frame_number,

                    "difference": score

                })

        previous_frame = frame.copy()

        frame_number += 1


    capture.release()


    output_file = os.path.join(
        case_dir,
        "duplicate_frames.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            duplicates,
            file,
            indent=4
        )

    return duplicates


# ============================================================
# DETECCION DE CORTES
# ============================================================

def detect_cuts(
    video_path,
    case_dir,
    threshold=35
):

    capture = cv2.VideoCapture(
        video_path
    )

    cuts = []

    previous_frame = None

    frame_number = 0

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    while True:

        success, frame = capture.read()

        if not success:

            break

        if previous_frame is not None:

            small_current = cv2.resize(
                frame,
                (320, 180)
            )

            small_previous = cv2.resize(
                previous_frame,
                (320, 180)
            )

            score = frame_difference(
                small_previous,
                small_current
            )

            if score >= threshold:

                timestamp = (
                    frame_number / fps
                    if fps > 0
                    else 0
                )

                cuts.append({

                    "frame": frame_number,

                    "time": format_time(
                        timestamp
                    ),

                    "difference": score

                })

        previous_frame = frame.copy()

        frame_number += 1


    capture.release()


    output_file = os.path.join(
        case_dir,
        "possible_cuts.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            cuts,
            file,
            indent=4
        )

    return cuts


# ============================================================
# CAMBIOS DE ILUMINACION
# ============================================================

def detect_lighting_changes(
    video_path,
    case_dir,
    threshold=30
):

    capture = cv2.VideoCapture(
        video_path
    )

    changes = []

    previous_brightness = None

    frame_number = 0

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    while True:

        success, frame = capture.read()

        if not success:

            break

        small = cv2.resize(
            frame,
            (320, 180)
        )

        gray = cv2.cvtColor(
            small,
            cv2.COLOR_BGR2GRAY
        )

        brightness = float(
            np.mean(gray)
        )

        if previous_brightness is not None:

            difference = abs(
                brightness -
                previous_brightness
            )

            if difference >= threshold:

                timestamp = (
                    frame_number / fps
                    if fps > 0
                    else 0
                )

                changes.append({

                    "frame": frame_number,

                    "time": format_time(
                        timestamp
                    ),

                    "brightness": brightness,

                    "difference": difference

                })

        previous_brightness = brightness

        frame_number += 1


    capture.release()


    output_file = os.path.join(
        case_dir,
        "lighting_changes.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            changes,
            file,
            indent=4
        )

    return changes


# ============================================================
# INCONSISTENCIAS VISUALES
# ============================================================

def detect_visual_anomalies(
    video_path,
    case_dir
):

    capture = cv2.VideoCapture(
        video_path
    )

    anomalies = []

    frame_number = 0

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    while True:

        success, frame = capture.read()

        if not success:

            break

        small = cv2.resize(
            frame,
            (320, 180)
        )

        gray = cv2.cvtColor(
            small,
            cv2.COLOR_BGR2GRAY
        )

        brightness = float(
            np.mean(gray)
        )

        sharpness = float(
            cv2.Laplacian(
                gray,
                cv2.CV_64F
            ).var()
        )

        if (
            brightness < 15
            or brightness > 245
            or sharpness < 8
        ):

            timestamp = (
                frame_number / fps
                if fps > 0
                else 0
            )

            anomalies.append({

                "frame": frame_number,

                "time": format_time(
                    timestamp
                ),

                "brightness": brightness,

                "sharpness": sharpness

            })

        frame_number += 1


    capture.release()


    output_file = os.path.join(
        case_dir,
        "visual_anomalies.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            anomalies,
            file,
            indent=4
        )

    return anomalies


# ============================================================
# ANOMALIAS TEMPORALES
# ============================================================

def detect_temporal_anomalies(
    video_path,
    case_dir,
    threshold=45
):

    capture = cv2.VideoCapture(
        video_path
    )

    frames = []

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    while True:

        success, frame = capture.read()

        if not success:

            break

        small = cv2.resize(
            frame,
            (160, 90)
        )

        gray = cv2.cvtColor(
            small,
            cv2.COLOR_BGR2GRAY
        )

        frames.append(
            gray
        )

    capture.release()


    anomalies = []


    for index in range(
        1,
        len(frames) - 1
    ):

        previous_frame = frames[
            index - 1
        ]

        current_frame = frames[
            index
        ]

        next_frame = frames[
            index + 1
        ]


        previous_difference = float(
            np.mean(
                cv2.absdiff(
                    previous_frame,
                    current_frame
                )
            )
        )


        next_difference = float(
            np.mean(
                cv2.absdiff(
                    current_frame,
                    next_frame
                )
            )
        )


        bridge_difference = float(
            np.mean(
                cv2.absdiff(
                    previous_frame,
                    next_frame
                )
            )
        )


        if bridge_difference >= threshold:

            timestamp = (
                index / fps
                if fps > 0
                else 0
            )

            anomalies.append({

                "frame": index,

                "time": format_time(
                    timestamp
                ),

                "previous_difference":
                    previous_difference,

                "next_difference":
                    next_difference,

                "temporal_jump":
                    bridge_difference

            })


    output_file = os.path.join(
        case_dir,
        "temporal_anomalies.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            anomalies,
            file,
            indent=4
        )

    return anomalies


# ============================================================
# GENERAR INFORME HTML
# ============================================================

def generate_html_report(
    video_path,
    case_dir,
    results
):

    report_path = os.path.join(
        case_dir,
        "forensic_report.html"
    )


    video_info = get_video_info(
        video_path
    )


    hashes = results.get(
        "hashes",
        {}
    )


    duplicate_count = len(
        results.get(
            "duplicates",
            []
        )
    )


    cut_count = len(
        results.get(
            "cuts",
            []
        )
    )


    lighting_count = len(
        results.get(
            "lighting",
            []
        )
    )


    visual_count = len(
        results.get(
            "visual",
            []
        )
    )


    temporal_count = len(
        results.get(
            "temporal",
            []
        )
    )


    escaped_video = html.escape(
        video_path
    )


    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(f"""
<!DOCTYPE html>

<html lang="es">

<head>

<meta charset="UTF-8">

<title>Video Forensics Report</title>

<style>

body {{
    background: #020607;
    color: #B7F7FF;
    font-family: monospace;
    margin: 40px;
}}

.container {{
    max-width: 1100px;
    margin: auto;
}}

h1 {{
    color: #00D9E8;
}}

h2 {{
    color: #38E0B5;
    border-bottom: 1px solid #007C86;
    padding-bottom: 8px;
}}

.card {{
    background: #061011;
    border: 1px solid #007C86;
    padding: 20px;
    margin-top: 20px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

td, th {{
    border: 1px solid #007C86;
    padding: 10px;
    text-align: left;
}}

th {{
    color: #00D9E8;
}}

.alert {{
    color: #FFD166;
}}

</style>

</head>

<body>

<div class="container">

<h1>HIDRA ACADEMY</h1>

<h2>VIDEO FORENSICS LAB - INFORME FORENSE</h2>

<div class="card">

<b>Fecha:</b>
{datetime.now()}<br>

<b>Archivo:</b>
{escaped_video}<br>

<b>Directorio del caso:</b>
{html.escape(case_dir)}

</div>


<h2>INFORMACIÓN TÉCNICA</h2>

<div class="card">

<table>

<tr>
<th>Propiedad</th>
<th>Valor</th>
</tr>

<tr>
<td>FPS</td>
<td>{video_info["fps"]}</td>
</tr>

<tr>
<td>Total Frames</td>
<td>{video_info["frames"]}</td>
</tr>

<tr>
<td>Resolución</td>
<td>
{video_info["width"]}
x
{video_info["height"]}
</td>
</tr>

<tr>
<td>Duración</td>
<td>
{format_time(video_info["duration"])}
</td>
</tr>

</table>

</div>


<h2>INTEGRIDAD CRIPTOGRÁFICA</h2>

<div class="card">

<table>

<tr>
<th>Algoritmo</th>
<th>Hash</th>
</tr>

""")

        for algorithm, value in hashes.items():

            file.write(f"""

<tr>
<td>{algorithm}</td>
<td>{value}</td>
</tr>

""")


        file.write(f"""

</table>

</div>


<h2>RESULTADOS DEL ANÁLISIS</h2>

<div class="card">

<table>

<tr>
<th>Módulo</th>
<th>Indicadores detectados</th>
</tr>

<tr>
<td>Frames duplicados</td>
<td>{duplicate_count}</td>
</tr>

<tr>
<td>Posibles cortes</td>
<td>{cut_count}</td>
</tr>

<tr>
<td>Cambios de iluminación</td>
<td>{lighting_count}</td>
</tr>

<tr>
<td>Inconsistencias visuales</td>
<td>{visual_count}</td>
</tr>

<tr>
<td>Anomalías temporales</td>
<td>{temporal_count}</td>
</tr>

</table>

</div>


<h2>NOTA FORENSE</h2>

<div class="card alert">

Los resultados representan indicadores técnicos
generados mediante análisis automatizado.

La presencia de una anomalía no constituye,
por sí sola, prueba concluyente de manipulación.

Los hallazgos deben ser correlacionados con
metadatos, estructura del archivo, evidencia
original, timestamps y revisión manual.

</div>

</div>

</body>

</html>

""")

    return report_path


# ============================================================
# INTERFAZ
# ============================================================

class VideoForensicsApp:

    def __init__(self, root):

        self.root = root

        self.root.title(APP_NAME)

        # Tamaño reducido
        self.root.geometry(
            "1120x720"
        )

        self.root.minsize(
            950,
            650
        )

        self.root.configure(
            bg=BACKGROUND
        )


        self.video_path = None

        self.case_dir = None

        self.analysis_results = {}

        self.video_capture = None

        self.playing = False

        self.current_photo = None

        self.log_queue = queue.Queue()


        self.create_interface()

        self.process_log_queue()


    # ========================================================
    # INTERFAZ
    # ========================================================

    def create_interface(self):

        self.main = tk.Frame(
            self.root,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.main.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=15
        )


        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = tk.Frame(
            self.main,
            bg=PANEL
        )

        header.pack(
            fill="x",
            padx=20,
            pady=15
        )


        left = tk.Frame(
            header,
            bg=PANEL
        )

        left.pack(
            side="left"
        )


        tk.Label(
            left,
            text="HIDRA ACADEMY",
            fg=TEXT_DIM,
            bg=PANEL,
            font=(
                "Courier New",
                10,
                "bold"
            )
        ).pack(
            anchor="w"
        )


        tk.Label(
            left,
            text="VIDEO FORENSICS LAB",
            fg=TEXT_TITLE,
            bg=PANEL,
            font=(
                "Courier New",
                18,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(5, 0)
        )


        status = tk.Frame(
            header,
            bg=PANEL
        )

        status.pack(
            side="right"
        )


        tk.Label(
            status,
            text="●",
            fg=SUCCESS,
            bg=PANEL,
            font=(
                "Arial",
                13
            )
        ).pack(
            side="left"
        )


        tk.Label(
            status,
            text=" SISTEMA ACTIVO",
            fg=SUCCESS,
            bg=PANEL,
            font=(
                "Courier New",
                10,
                "bold"
            )
        ).pack(
            side="left"
        )


        tk.Frame(
            self.main,
            bg=BORDER_SOFT,
            height=1
        ).pack(
            fill="x",
            padx=20
        )


        # ----------------------------------------------------
        # CONTENIDO
        # ----------------------------------------------------

        content = tk.Frame(
            self.main,
            bg=PANEL
        )

        content.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=15
        )


        content.grid_columnconfigure(
            0,
            weight=3
        )

        content.grid_columnconfigure(
            1,
            weight=2
        )

        content.grid_rowconfigure(
            0,
            weight=1
        )


        self.left_panel = tk.Frame(
            content,
            bg=PANEL,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1
        )

        self.left_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8)
        )


        self.right_panel = tk.Frame(
            content,
            bg=PANEL,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1
        )

        self.right_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(8, 0)
        )


        self.create_left_panel()

        self.create_right_panel()


        # ----------------------------------------------------
        # TERMINAL
        # ----------------------------------------------------

        self.create_terminal()


    # ========================================================
    # PANEL IZQUIERDO
    # ========================================================

    def create_left_panel(self):

        self.left_panel.grid_rowconfigure(
            0,
            weight=1
        )


        # Vista previa

        preview_frame = tk.Frame(
            self.left_panel,
            bg=PANEL_DARK,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1
        )

        preview_frame.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=12
        )


        self.preview_label = tk.Label(
            preview_frame,
            text="VIDEO\nFORENSIC\nANALYSIS",
            fg=BORDER,
            bg=PANEL_DARK,
            font=(
                "Courier New",
                22,
                "bold"
            ),
            justify="center"
        )

        self.preview_label.pack(
            fill="both",
            expand=True
        )


        # Botones

        buttons_frame = tk.Frame(
            self.left_panel,
            bg=PANEL
        )

        buttons_frame.pack(
            fill="x",
            padx=12,
            pady=(0, 8)
        )


        buttons_frame.grid_columnconfigure(
            0,
            weight=1
        )

        buttons_frame.grid_columnconfigure(
            1,
            weight=1
        )


        buttons = [

            (
                "⌗  HASH",
                self.start_hash
            ),

            (
                "▤  METADATOS",
                self.start_metadata
            ),

            (
                "▣  EXTRAER FRAMES",
                self.start_extract_frames
            ),

            (
                "▣  DUPLICADOS",
                self.start_duplicates
            ),

            (
                "✂  CORTES",
                self.start_cuts
            ),

            (
                "☼  ILUMINACIÓN",
                self.start_lighting
            ),

            (
                "◉  VISUAL",
                self.start_visual
            ),

            (
                "◷  TEMPORAL",
                self.start_temporal
            )

        ]


        for index, data in enumerate(buttons):

            text = data[0]

            command = data[1]

            button = self.create_button(
                buttons_frame,
                text,
                command
            )

            button.grid(
                row=index // 2,
                column=index % 2,
                sticky="ew",
                padx=5,
                pady=5
            )


        self.create_button(
            self.left_panel,
            "⚡  EJECUTAR ANÁLISIS COMPLETO",
            self.start_full_analysis
        ).pack(
            fill="x",
            padx=12,
            pady=4
        )


        self.create_button(
            self.left_panel,
            "▤  GENERAR INFORME HTML",
            self.start_html_report
        ).pack(
            fill="x",
            padx=12,
            pady=(4, 12)
        )


    # ========================================================
    # PANEL DERECHO
    # ========================================================

    def create_right_panel(self):

        tk.Label(
            self.right_panel,
            text="EVIDENCIA DIGITAL",
            fg=BORDER,
            bg=PANEL,
            font=(
                "Courier New",
                10,
                "bold"
            )
        ).pack(
            anchor="w",
            padx=18,
            pady=(18, 10)
        )


        tk.Label(
            self.right_panel,
            text="ARCHIVO SELECCIONADO",
            fg=TEXT_DIM,
            bg=PANEL,
            font=(
                "Courier New",
                9,
                "bold"
            )
        ).pack(
            anchor="w",
            padx=18
        )


        self.file_name_label = tk.Label(
            self.right_panel,
            text="Ningún archivo seleccionado",
            fg=TEXT_DIM,
            bg=PANEL_DARK,
            anchor="w",
            padx=10,
            pady=10,
            wraplength=300,
            font=(
                "Courier New",
                9
            ),
            highlightbackground=BORDER_SOFT,
            highlightthickness=1
        )

        self.file_name_label.pack(
            fill="x",
            padx=18,
            pady=8
        )


        self.create_button(
            self.right_panel,
            "▶  SELECCIONAR VIDEO",
            self.select_video
        ).pack(
            fill="x",
            padx=18,
            pady=8
        )


        tk.Frame(
            self.right_panel,
            bg=BORDER_SOFT,
            height=1
        ).pack(
            fill="x",
            padx=18,
            pady=12
        )


        tk.Label(
            self.right_panel,
            text="FLUJO FORENSE",
            fg=BORDER,
            bg=PANEL,
            font=(
                "Courier New",
                10,
                "bold"
            )
        ).pack(
            anchor="w",
            padx=18,
            pady=(0, 10)
        )


        for step in [

            "✓  PRESERVAR",
            "✓  ANALIZAR",
            "✓  DOCUMENTAR"

        ]:

            tk.Label(
                self.right_panel,
                text=step,
                fg=SUCCESS,
                bg=PANEL,
                font=(
                    "Courier New",
                    9,
                    "bold"
                )
            ).pack(
                anchor="w",
                padx=25,
                pady=7
            )


        tk.Frame(
            self.right_panel,
            bg=BORDER_SOFT,
            height=1
        ).pack(
            fill="x",
            padx=18,
            pady=14
        )


        tk.Label(
            self.right_panel,
            text="ESTADO DEL CASO",
            fg=TEXT_DIM,
            bg=PANEL,
            font=(
                "Courier New",
                9,
                "bold"
            )
        ).pack(
            anchor="w",
            padx=18
        )


        self.case_status = tk.Label(
            self.right_panel,
            text="○ SIN EVIDENCIA",
            fg=WARNING,
            bg=PANEL,
            font=(
                "Courier New",
                9,
                "bold"
            )
        )

        self.case_status.pack(
            anchor="w",
            padx=18,
            pady=8
        )


    # ========================================================
    # BOTON
    # ========================================================

    def create_button(
        self,
        parent,
        text,
        command
    ):

        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=PANEL_BUTTON,
            fg=TEXT,
            activebackground=PANEL_HOVER,
            activeforeground=BORDER,
            font=(
                "Courier New",
                9,
                "bold"
            ),
            relief="flat",
            bd=0,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1,
            cursor="hand2",
            pady=8
        )


        button.bind(
            "<Enter>",
            lambda event:
            button.configure(
                bg=PANEL_HOVER,
                fg=BORDER
            )
        )


        button.bind(
            "<Leave>",
            lambda event:
            button.configure(
                bg=PANEL_BUTTON,
                fg=TEXT
            )
        )


        return button


    # ========================================================
    # TERMINAL
    # ========================================================

    def create_terminal(self):

        terminal_frame = tk.Frame(
            self.main,
            bg=PANEL_DARK,
            highlightbackground=BORDER_SOFT,
            highlightthickness=1
        )

        terminal_frame.pack(
            fill="both",
            expand=False,
            padx=20,
            pady=(0, 15)
        )


        tk.Label(
            terminal_frame,
            text="[ ACTIVITY LOG / FORENSIC TERMINAL ]",
            fg=BORDER,
            bg=PANEL_DARK,
            font=(
                "Courier New",
                10,
                "bold"
            )
        ).pack(
            anchor="w",
            padx=12,
            pady=7
        )


        self.terminal = scrolledtext.ScrolledText(
            terminal_frame,
            height=6,
            bg="#020B0C",
            fg=TEXT_DIM,
            insertbackground=BORDER,
            font=(
                "Courier New",
                9
            ),
            relief="flat",
            bd=0
        )

        self.terminal.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=(0, 8)
        )


    # ========================================================
    # LOG SEGURO PARA THREADS
    # ========================================================

    def log(self, message):

        current_time = datetime.now().strftime(
            "%H:%M:%S"
        )

        self.log_queue.put(
            f"[{current_time}] {message}"
        )


    def process_log_queue(self):

        try:

            while True:

                message = self.log_queue.get_nowait()

                self.terminal.insert(
                    tk.END,
                    message + "\n"
                )

                self.terminal.see(
                    tk.END
                )

        except queue.Empty:

            pass


        self.root.after(
            100,
            self.process_log_queue
        )


    # ========================================================
    # VALIDAR VIDEO
    # ========================================================

    def check_video(self):

        if not self.video_path:

            messagebox.showwarning(
                "Evidencia requerida",
                "Seleccione un video primero."
            )

            return False

        return True


    # ========================================================
    # SELECCIONAR VIDEO
    # ========================================================

    def select_video(self):

        file_path = filedialog.askopenfilename(

            title="Seleccionar evidencia de video",

            filetypes=[

                (
                    "Videos",
                    "*.mp4 *.avi *.mov *.mkv *.wmv *.webm *.flv"
                ),

                (
                    "Todos",
                    "*.*"
                )

            ]

        )


        if not file_path:

            return


        self.video_path = file_path

        self.case_dir = create_case_directory(
            file_path
        )

        self.analysis_results = {}


        file_name = os.path.basename(
            file_path
        )


        self.file_name_label.configure(
            text=file_name,
            fg=SUCCESS
        )


        self.case_status.configure(
            text="● EVIDENCIA CARGADA",
            fg=SUCCESS
        )


        self.log(
            f"[+] Video seleccionado: {file_name}"
        )

        self.log(
            f"[CASE] Directorio: {self.case_dir}"
        )


        self.show_video_preview()


    # ========================================================
    # VISTA PREVIA VIDEO
    # ========================================================

    def show_video_preview(self):

        if not self.video_path:

            return


        capture = cv2.VideoCapture(
            self.video_path
        )

        success, frame = capture.read()

        capture.release()


        if not success:

            self.log(
                "[ERROR] No se pudo generar vista previa."
            )

            return


        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )


        image = Image.fromarray(
            frame
        )


        image.thumbnail(
            (550, 260)
        )


        self.current_photo = ImageTk.PhotoImage(
            image
        )


        self.preview_label.configure(
            image=self.current_photo,
            text=""
        )


        self.preview_label.image = self.current_photo


    # ========================================================
    # EJECUTAR FUNCION EN THREAD
    # ========================================================

    def run_background(
        self,
        function
    ):

        thread = threading.Thread(
            target=function,
            daemon=True
        )

        thread.start()


    # ========================================================
    # HASH
    # ========================================================

    def start_hash(self):

        if self.check_video():

            self.run_background(
                self.hash_analysis
            )


    def hash_analysis(self):

        try:

            self.log(
                "[ANALYSIS] Generando hashes..."
            )

            hashes = generate_hashes(
                self.video_path,
                self.case_dir
            )

            self.analysis_results[
                "hashes"
            ] = hashes

            self.log(
                "[SUCCESS] Hashes generados."
            )

            self.log(
                f"[SHA256] "
                f"{hashes['SHA256']}"
            )

        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


    # ========================================================
    # METADATOS
    # ========================================================

    def start_metadata(self):

        if self.check_video():

            self.run_background(
                self.metadata_analysis
            )


    def metadata_analysis(self):

        try:

            self.log(
                "[ANALYSIS] Extrayendo metadatos..."
            )

            path = extract_metadata(
                self.video_path,
                self.case_dir
            )

            self.analysis_results[
                "metadata"
            ] = path

            self.log(
                "[SUCCESS] Metadatos extraídos."
            )

        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


    # ========================================================
    # EXTRAER FRAMES
    # ========================================================

    def start_extract_frames(self):

        if self.check_video():

            self.run_background(
                self.frames_analysis
            )


    def frames_analysis(self):

        try:

            self.log(
                "[ANALYSIS] Extrayendo frames..."
            )

            directory, total = extract_frames(
                self.video_path,
                self.case_dir
            )

            self.analysis_results[
                "frames"
            ] = {

                "directory": directory,

                "total": total

            }

            self.log(
                f"[SUCCESS] {total} frames extraídos."
            )

        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


    # ========================================================
    # DUPLICADOS
    # ========================================================

    def start_duplicates(self):

        if self.check_video():

            self.run_background(
                self.duplicates_analysis
            )


    def duplicates_analysis(self):

        try:

            self.log(
                "[ANALYSIS] Buscando frames duplicados..."
            )

            results = detect_duplicate_frames(
                self.video_path,
                self.case_dir
            )

            self.analysis_results[
                "duplicates"
            ] = results

            self.log(
                f"[RESULT] "
                f"{len(results)} posibles duplicados."
            )

        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


    # ========================================================
    # CORTES
    # ========================================================

    def start_cuts(self):

        if self.check_video():

            self.run_background(
                self.cuts_analysis
            )


    def cuts_analysis(self):

        try:

            self.log(
                "[ANALYSIS] Detectando posibles cortes..."
            )

            results = detect_cuts(
                self.video_path,
                self.case_dir
            )

            self.analysis_results[
                "cuts"
            ] = results

            self.log(
                f"[RESULT] "
                f"{len(results)} posibles cortes."
            )

        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


    # ========================================================
    # ILUMINACION
    # ========================================================

    def start_lighting(self):

        if self.check_video():

            self.run_background(
                self.lighting_analysis
            )


    def lighting_analysis(self):

        try:

            self.log(
                "[ANALYSIS] Analizando iluminación..."
            )

            results = detect_lighting_changes(
                self.video_path,
                self.case_dir
            )

            self.analysis_results[
                "lighting"
            ] = results

            self.log(
                f"[RESULT] "
                f"{len(results)} cambios detectados."
            )

        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


    # ========================================================
    # VISUAL
    # ========================================================

    def start_visual(self):

        if self.check_video():

            self.run_background(
                self.visual_analysis
            )


    def visual_analysis(self):

        try:

            self.log(
                "[ANALYSIS] Buscando inconsistencias visuales..."
            )

            results = detect_visual_anomalies(
                self.video_path,
                self.case_dir
            )

            self.analysis_results[
                "visual"
            ] = results

            self.log(
                f"[RESULT] "
                f"{len(results)} anomalías visuales."
            )

        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


    # ========================================================
    # TEMPORAL
    # ========================================================

    def start_temporal(self):

        if self.check_video():

            self.run_background(
                self.temporal_analysis
            )


    def temporal_analysis(self):

        try:

            self.log(
                "[ANALYSIS] Analizando discontinuidades temporales..."
            )

            results = detect_temporal_anomalies(
                self.video_path,
                self.case_dir
            )

            self.analysis_results[
                "temporal"
            ] = results

            self.log(
                f"[RESULT] "
                f"{len(results)} anomalías temporales."
            )

        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


    # ========================================================
    # ANALISIS COMPLETO
    # ========================================================

    def start_full_analysis(self):

        if self.check_video():

            self.run_background(
                self.full_analysis
            )


    def full_analysis(self):

        try:

            self.log(
                "[START] INICIANDO ANÁLISIS FORENSE COMPLETO"
            )


            self.log(
                "[1/8] Generando hashes..."
            )

            self.analysis_results[
                "hashes"
            ] = generate_hashes(
                self.video_path,
                self.case_dir
            )


            self.log(
                "[2/8] Extrayendo metadatos..."
            )

            self.analysis_results[
                "metadata"
            ] = extract_metadata(
                self.video_path,
                self.case_dir
            )


            self.log(
                "[3/8] Extrayendo frames..."
            )

            directory, total = extract_frames(
                self.video_path,
                self.case_dir
            )

            self.analysis_results[
                "frames"
            ] = {

                "directory": directory,

                "total": total

            }


            self.log(
                "[4/8] Analizando duplicados..."
            )

            self.analysis_results[
                "duplicates"
            ] = detect_duplicate_frames(
                self.video_path,
                self.case_dir
            )


            self.log(
                "[5/8] Detectando cortes..."
            )

            self.analysis_results[
                "cuts"
            ] = detect_cuts(
                self.video_path,
                self.case_dir
            )


            self.log(
                "[6/8] Analizando iluminación..."
            )

            self.analysis_results[
                "lighting"
            ] = detect_lighting_changes(
                self.video_path,
                self.case_dir
            )


            self.log(
                "[7/8] Analizando inconsistencias visuales..."
            )

            self.analysis_results[
                "visual"
            ] = detect_visual_anomalies(
                self.video_path,
                self.case_dir
            )


            self.log(
                "[8/8] Analizando anomalías temporales..."
            )

            self.analysis_results[
                "temporal"
            ] = detect_temporal_anomalies(
                self.video_path,
                self.case_dir
            )


            self.log(
                "[SUCCESS] ANÁLISIS COMPLETO FINALIZADO."
            )

        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


    # ========================================================
    # INFORME HTML
    # ========================================================

    def start_html_report(self):

        if self.check_video():

            self.run_background(
                self.html_report
            )


    def html_report(self):

        try:

            self.log(
                "[REPORT] Generando informe HTML..."
            )

            # Si todavía no hay hash,
            # se genera automáticamente.

            if "hashes" not in self.analysis_results:

                self.analysis_results[
                    "hashes"
                ] = generate_hashes(
                    self.video_path,
                    self.case_dir
                )


            report_path = generate_html_report(
                self.video_path,
                self.case_dir,
                self.analysis_results
            )


            self.log(
                "[SUCCESS] Informe HTML generado."
            )

            self.log(
                f"[REPORT] {report_path}"
            )


        except Exception as error:

            self.log(
                f"[ERROR] {error}"
            )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = VideoForensicsApp(
        root
    )

    root.mainloop()