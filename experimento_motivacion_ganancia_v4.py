import streamlit as st
import random
import time
import pandas as pd # Se mantiene por si hay otras operaciones de datos, aunque no se use activamente

# --- Configuración de la página de Streamlit ---
st.set_page_config(layout="centered", page_title="Experimento de Motivación Cognitiva (Ganancia)", 
                   initial_sidebar_state="collapsed") # Colapsa el sidebar por defecto

# --- Parámetros del experimento (constantes) ---
SUBTRACT_VALUE = 13
START_NUMBER = 1000  # Tarea: inicia en 1000
TARGET_THRESHOLD = 900 # Tarea: termina al sobrepasar 900
MAX_BLOCKS = 4
BLOCK_DURATION = 60  # segundos por bloque
PAUSE_DURATION = 10 # segundos de pausa entre bloques

# --- Inicialización del estado de la sesión de Streamlit ---
def initialize_session_state():
    """Initializes session state variables for the experiment."""
    # Reinicia todas las variables para asegurar un "inicio desde cero"
    for key in st.session_state.keys():
        del st.session_state[key]

    st.session_state.experiment_phase = 'WELCOME'
    st.session_state.group = "Ganancia" # FIJADO A GANANCIA
    st.session_state.initial_money = 100000 # Dinero inicial para el grupo de Ganancia
    st.session_state.current_money = st.session_state.initial_money
    st.session_state.current_block = 0 
    st.session_state.current_sequence_number = START_NUMBER 
    st.session_state.errors_in_current_block = 0
    st.session_state.feedback_message = ""
    st.session_state.feedback_color = "black"
    st.session_state.block_start_time = 0
    st.session_state.blocks_results = [] # Almacena {block, success, errors, time_taken_s}
    st.session_state.block_completed_successfully_counter = 0 # Contador para lógica de premios
    st.session_state.last_input_value = "" # Para controlar el valor del text_input
    st.session_state.should_autofocus = False # Flag para autofoco
    st.session_state.final_summary_data = {} # Para almacenar datos del resumen final

# --- Funciones de navegación y lógica del experimento ---

def next_phase(phase):
    """Cambia la fase del experimento y fuerza un rerender de Streamlit."""
    st.session_state.experiment_phase = phase
    st.rerun() 

def start_experiment_task():
    """Reinicia variables para la tarea principal y comienza el primer bloque."""
    initialize_session_state() # Reinicia todo el estado para empezar realmente de cero
    # Después de initialize_session_state, el estado ya estará listo para el WELCOME, 
    # pero queremos ir directamente a la tarea, así que ajustamos la fase y llamamos a start_new_block
    st.session_state.experiment_phase = 'EXPERIMENT' 
    st.session_state.current_block = 0 # Asegura que start_new_block lo incremente a 1
    start_new_block()

def start_new_block():
    """Inicia un nuevo bloque de la tarea o finaliza el experimento."""
    if st.session_state.current_block < MAX_BLOCKS:
        st.session_state.current_block += 1
        st.session_state.current_sequence_number = START_NUMBER 
        st.session_state.errors_in_current_block = 0
        st.session_state.feedback_message = ""
        st.session_state.feedback_color = "black"
        st.session_state.block_start_time = time.time() # Registra el tiempo de inicio del bloque
        st.session_state.last_input_value = "" # Limpia el input para el nuevo bloque
        st.session_state.should_autofocus = True # Activa autofoco para este nuevo bloque
        next_phase('EXPERIMENT') # Asegura que se renderice la fase EXPERIMENT
    else:
        # Calcular los datos del resumen final justo antes de pasar a la fase RESULTS
        calculate_and_store_final_summary()
        next_phase('RESULTS')

def handle_block_end(success):
    """
    Gestiona el final de un bloque (exitoso o fallido), actualiza el dinero,
    y prepara el siguiente bloque (o la pausa).
    """
    block_duration_taken = time.time() - st.session_state.block_start_time
    
    # Se considera fallido si el tiempo se agotó O si la lógica de la tarea lo marcó como fallido
    block_was_timed_out = block_duration_taken > BLOCK_DURATION

    money_change = 0
    message_summary = ""

    if success and not block_was_timed_out:
        st.session_state.blocks_results.append({
            "block": st.session_state.current_block,
            "success": True,
            "errors": st.session_state.errors_in_current_block,
            "time_taken_s": round(block_duration_taken, 2)
        })
        st.session_state.block_completed_successfully_counter += 1 
        
        # Lógica de Ganancia basada en el contador de bloques exitosos
        if st.session_state.block_completed_successfully_counter == 1: money_change = 10000
        elif st.session_state.block_completed_successfully_counter == 2: money_change = 20000
        elif st.session_state.block_completed_successfully_counter == 3: money_change = 20000
        elif st.session_state.block_completed_successfully_counter == 4: money_change = 50000
        
        st.session_state.current_money += money_change
        message_summary = f"¡Ganaste ${money_change:,.0f}!"
        st.session_state.feedback_color = "green"

    else: # Bloque Fallido (por error o por tiempo agotado)
        st.session_state.blocks_results.append({
            "block": st.session_state.current_block,
            "success": False,
            "errors": st.session_state.errors_in_current_block,
            "time_taken_s": round(block_duration_taken, 2) # Tiempo hasta el fallo o timeout
        })
        # En la modalidad de Ganancia, no se pierde dinero por fallar un bloque.
        message_summary = "Bloque no completado a tiempo."
        st.session_state.feedback_color = "red"

    st.session_state.feedback_message = f"Bloque {st.session_state.current_block} Finalizado. {message_summary}"
    
    st.session_state.current_money = st.session_state.current_money # Fuerza la actualización del estado

    # Si quedan más bloques, introduce una pausa
    if st.session_state.current_block < MAX_BLOCKS:
        st.session_state.pause_message = f"Fin del Bloque {st.session_state.current_block}. Tómate un breve descanso."
        st.session_state.pause_end_time = time.time() + PAUSE_DURATION
        next_phase('PAUSE_BETWEEN_BLOCKS')
    else:
        # Si no quedan más bloques, pasa directamente a los resultados finales
        calculate_and_store_final_summary() 
        next_phase('RESULTS')

def process_user_input(user_answer_str):
    """
    Procesa la respuesta del usuario para la tarea aritmética.
    Esta función se llama cuando se envía el formulario.
    """
    
    # 1. Primero, verificar si el tiempo del bloque ya expiró ANTES de procesar la respuesta.
    if time.time() - st.session_state.block_start_time > BLOCK_DURATION:
        st.session_state.feedback_message = f"¡El tiempo para el Bloque {st.session_state.current_block} se agotó antes de tu respuesta!"
        st.session_state.feedback_color = "orange"
        handle_block_end(False) # Bloque fallido por tiempo
        return # Termina la función aquí

    # 2. Si hay tiempo, procesar la respuesta
    try:
        user_answer_int = int(user_answer_str)
        correct_answer_calc = st.session_state.current_sequence_number - SUBTRACT_VALUE

        if user_answer_int == correct_answer_calc:
            st.session_state.current_sequence_number = user_answer_int
            st.session_state.feedback_message = "¡Correcto!"
            st.session_state.feedback_color = "green"
            st.session_state.last_input_value = "" # Vaciar input si es correcto
            
            if st.session_state.current_sequence_number <= TARGET_THRESHOLD:
                handle_block_end(True) # Bloque completado con éxito
            else:
                st.rerun() # Para actualizar la UI con el nuevo número y feedback
        else:
            st.session_state.errors_in_current_block += 1
            st.session_state.feedback_message = f"Incorrecto. Reiniciando secuencia desde {START_NUMBER}." 
            st.session_state.feedback_color = "red"
            st.session_state.current_sequence_number = START_NUMBER # Reiniciar secuencia
            st.session_state.last_input_value = "" # Vaciar input en error numérico
            st.rerun()
    except ValueError:
        st.session_state.feedback_message = "Por favor, ingresa un número válido."
        st.session_state.feedback_color = "orange"
        st.session_state.last_input_value = "" # Vaciar input en error no numérico
        st.rerun()

def calculate_and_store_final_summary():
    """Calculates summary data for final display and stores it in session state."""
    total_errors = sum(block_res['errors'] for block_res in st.session_state.blocks_results)

    money_difference = st.session_state.current_money - st.session_state.initial_money
    money_outcome_description = ""
    if money_difference > 0:
        money_outcome_description = f"Ganancia Total: ${money_difference:,.0f}"
    else: 
        money_outcome_description = "No hubo ganancias."

    st.session_state.final_summary_data = {
        "total_errors": total_errors,
        "money_outcome_description": money_outcome_description,
    }

# --- Global styles for the Streamlit application ---
st.markdown("""
<style>
/* Custom font Inter */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
html, body, [class*="st-"] {
    font-family: 'Inter', sans-serif;
    text-align: center;
}
.stApp {
    background-color: #f0f0f0; /* Light grey background */
    padding: 20px;
}
/* Button styles */
.stButton>button {
    background-color: #007BFF; /* Primary blue - MODIFICADO para todos los botones */
    color: white;
    border-radius: 8px;
    font-weight: bold;
    padding: 10px 25px;
    margin: 5px;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.stButton>button:hover {
    background-color: #0056b3; /* Darker blue on hover */
    transform: translateY(-2px);
    box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
}
/* Specific styles for form submit button (overwritten to be blue too) */
/* Asegura que el botón de enviar dentro del formulario sea azul */
button[data-testid*="stFormSubmitButton"] {
    background-color: #007BFF !important; /* Mismo azul que los otros botones, forzado con !important */
    color: white !important; /* Letra blanca, forzado con !important */
}
button[data-testid*="stFormSubmitButton"]:hover {
    background-color: #0056b3 !important; /* Darker blue on hover, forzado con !important */
}

/* Text input field styles */
.stTextInput>div>div>input {
    text-align: center;
    font-size: 24px;
    padding: 10px;
    border-radius: 8px;
    border: 2px solid #ccc;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
    background-color: #ffffff; /* White background */
    color: #000000; /* Black text color */
}
.stTextInput>div>div>input:focus {
    border-color: #0056b3; /* Blue border on focus */
    outline: none;
    box-shadow: 0 0 0 0.2rem rgba(0, 86, 179, 0.25); /* Blue shadow on focus */
}
/* Slider styles */
.stSlider .st-fx { /* Track background */
    background: #e0e0e0;
    border-radius: 5px;
}
.stSlider .st-fy { /* Track fill */
    background: #007bff; 
    border-radius: 5px;
}
.stSlider .st-fz { /* Slider handle */
    background: #007bff;
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
/* Styles for titles and texts */
h1, h2, h3, h4 {
    color: #333333;
}
p {
    color: #555555;
    line-height: 1.6;
}
/* Content containers for cleaner design */
.element-container {
    padding: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# --- Render UI based on experiment phase ---

if st.session_state.experiment_phase == 'WELCOME':
    st.markdown("<h1 style='color:#333333; font-size:3.5em; font-weight:800;'>Bienvenido/a al Experimento de Motivación Cognitiva</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#666666; font-size:1.2em;'>Este experimento solo cuenta con la modalidad de Ganancia.</p>", unsafe_allow_html=True) 
    st.button("Comenzar Experimento", on_click=lambda: next_phase('INSTRUCTIONS'), 
              help="Haz clic para leer las instrucciones.",
              use_container_width=True)

elif st.session_state.experiment_phase == 'INSTRUCTIONS':
    st.markdown("<h2 style='color:#333333; font-size:2.5em; font-weight:bold;'>Instrucciones del Experimento</h2>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style='text-align: left; background-color: #ffffff; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);'>
            <p style='color:#333333; font-size:1.1em; line-height:1.6;'>
                ¡Hola!<br/><br/>
                Este experimento consta de una tarea aritmética simple que realizarás durante 
                <span style='font-weight:bold;'>{MAX_BLOCKS} bloques de {BLOCK_DURATION} segundo(s) cada uno</span>.<br/>
                Tu tarea es <span style='font-weight:bold;'>restar {SUBTRACT_VALUE} repetidamente, comenzando desde {START_NUMBER}</span>. 
                Por ejemplo: {START_NUMBER}, {START_NUMBER-SUBTRACT_VALUE}, {START_NUMBER-(2*SUBTRACT_VALUE)}, etc.<br/>
                Deberás ingresar cada resultado. Si cometes un error, la secuencia se 
                <span style='font-weight:bold; color:red;'>REINICIARÁ desde {START_NUMBER}</span> en ese mismo bloque.<br/>
                Para completar un bloque con éxito, debes hacer que el número actual sea 
                <span style='font-weight:bold;'>igual o menor que {TARGET_THRESHOLD}</span>.
            </p>
            <div style='background-color: #f9f9f9; padding: 20px; border-radius: 8px; margin-top: 20px; border: 1px solid #eee;'>
                <p style='font-size:1.2em; font-weight:bold; color:#4a235a;'>Estás en el grupo: <span style='color:#28a745;'>GANANCIA</span>.</p>
                <p style='color:#333333; font-size:1.05em;'>
                    <span style='font-weight:bold; color:#28a745;'>Lógica de Recompensa:</span><br/>
                    Comienzas con <span style='font-weight:bold;'>${st.session_state.initial_money:,.0f}</span> (ficticios).<br/>
                    Por cada bloque completado con éxito (independientemente del número de bloque):<br/>
                    - Si es tu **1er** bloque exitoso: ganas <span style='font-weight:bold;'>$10,000</span>.<br/>
                    - Si es tu **2do** bloque exitoso: ganas <span style='font-weight:bold;'>$20,000</span> adicionales.<br/>
                    - Si es tu **3er** bloque exitoso: ganas <span style='font-weight:bold;'>$20,000</span> adicionales.<br/>
                    - Si es tu **4to** bloque exitoso: ganas <span style='font-weight:bold;'>$50,000</span> adicionales.<br/>
                    <span style='font-weight:bold;'>Tu objetivo es ganar la mayor cantidad de dinero posible.</span>
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<p style='color:#333333; font-size:1.1em; line-height:1.6; margin-top:20px;'>Presiona <span style='font-weight:bold;'>'Entendido, Iniciar Experimento'</span> cuando estés listo/a.</p>", unsafe_allow_html=True)
    st.button("Entendido, Iniciar Experimento", on_click=start_experiment_task, 
              help="Haz clic para comenzar la tarea aritmética.",
              use_container_width=True)

elif st.session_state.experiment_phase == 'EXPERIMENT':
    st.markdown(f"<p style='color:#666666; font-size:1.1em; font-weight:semibold;'>Dinero Actual: <span style='color:#28a745; font-size:1.5em; font-weight:bold;'>${st.session_state.current_money:,.0f}</span></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#555555; font-size:1.1em;'>Bloque: <span style='font-weight:bold;'>{st.session_state.current_block} / {MAX_BLOCKS}</span></p>", unsafe_allow_html=True)
    
    # Calculate elapsed and estimated remaining time
    time_elapsed = round(time.time() - st.session_state.block_start_time, 1)
    time_remaining_estimated = max(0, BLOCK_DURATION - time_elapsed) # Ensure non-negative time
    
    st.markdown(f"<p style='color:#dc3545; font-size:1.2em; font-weight:bold;'>Tiempo restante estimado: {time_remaining_estimated:.0f}s</p>", unsafe_allow_html=True)
    
    st.markdown(f"<h3 style='color:#0056b3; font-size:3em; font-weight:bold; margin-top:30px;'>Número actual: {st.session_state.current_sequence_number}</h3>", unsafe_allow_html=True)
    
    # Use st.form to avoid double click issue
    with st.form(key=f"block_form_{st.session_state.current_block}"):
        # Placeholder is now empty
        user_answer = st.text_input("Ingresa tu respuesta:", 
                                    value=st.session_state.last_input_value, 
                                    placeholder="", 
                                    key=f"answer_input_{st.session_state.current_block}_form_input")
        
        submit_button = st.form_submit_button("Enviar Respuesta")

        if submit_button:
            # First, check if block time has expired BEFORE processing the answer.
            if time.time() - st.session_state.block_start_time > BLOCK_DURATION:
                st.session_state.feedback_message = f"¡El tiempo para el Bloque {st.session_state.current_block} se agotó antes de tu respuesta!"
                st.session_state.feedback_color = "orange"
                handle_block_end(False) # Mark block as failed due to timeout
                st.stop() # Stop execution to avoid processing the response
            
            # If time has not expired, process the answer
            try:
                user_answer_int = int(user_answer)
                correct_answer_calc = st.session_state.current_sequence_number - SUBTRACT_VALUE

                if user_answer_int == correct_answer_calc:
                    st.session_state.current_sequence_number = user_answer_int
                    st.session_state.feedback_message = "¡Correcto!"
                    st.session_state.feedback_color = "green"
                    st.session_state.last_input_value = "" # Clear input if correct
                    
                    if st.session_state.current_sequence_number <= TARGET_THRESHOLD:
                        handle_block_end(True) # Block completed successfully
                    else:
                        st.rerun() # To update UI with new number and feedback
                else:
                    st.session_state.errors_in_current_block += 1
                    st.session_state.feedback_message = f"Incorrecto. Reiniciando secuencia desde {START_NUMBER}." 
                    st.session_state.feedback_color = "red"
                    st.session_state.current_sequence_number = START_NUMBER # Reset sequence
                    st.session_state.last_input_value = "" # Clear input on incorrect numeric inputs
                    st.rerun()
            except ValueError:
                st.session_state.feedback_message = "Por favor, ingresa un número válido."
                st.session_state.feedback_color = "orange"
                st.session_state.last_input_value = "" # Clear input on non-numeric error
                st.rerun()

    # Feedback messages and error counter
    st.markdown(f"<p style='color:{st.session_state.feedback_color}; font-weight:bold;'>{st.session_state.feedback_message}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#6c757d;'>Errores en este bloque: {st.session_state.errors_in_current_block}</p>", unsafe_allow_html=True)

    # JavaScript para establecer el foco automáticamente
    input_key = f"answer_input_{st.session_state.current_block}_form_input"
    if st.session_state.should_autofocus:
        st.markdown(
            f"""
            <script>
                (function() {{
                    const inputElement = document.querySelector('[data-testid="stTextInput-Input-{input_key}"]');
                    if (inputElement) {{
                        inputElement.focus();
                        inputElement.select(); 
                    }}
                }})();
            </script>
            """,
            unsafe_allow_html=True
        )
        st.session_state.should_autofocus = False 


elif st.session_state.experiment_phase == 'PAUSE_BETWEEN_BLOCKS':
    st.markdown(f"<h2 style='color:#333333; font-size:2.5em; font-weight:bold;'>{st.session_state.pause_message}</h2>", unsafe_allow_html=True)
    
    time_until_next_block = max(0, int(st.session_state.pause_end_time - time.time()))
    st.info(f"El próximo bloque comenzará en {time_until_next_block} segundos.")

    if time_until_next_block > 0:
        time.sleep(1) 
        st.rerun()
    else:
        start_new_block() 


elif st.session_state.experiment_phase == 'RESULTS':
    # La función calculate_and_store_final_summary() ya se llama antes de entrar a esta fase
    # así que los datos ya están en st.session_state.final_summary_data

    st.markdown("<h2 style='color:#333333; font-size:2.5em; font-weight:bold;'>Experimento Finalizado</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#666666; font-size:1.2em;'>Tu dinero final es: <span style='color:#28a745; font-size:1.8em; font-weight:bold;'>${st.session_state.current_money:,.0f}</span></p>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='color:#333333; font-size:1.8em; font-weight:bold; margin-top:30px;'>Resumen de tu Desempeño:</h3>", unsafe_allow_html=True)

    st.markdown(f"<p style='font-size:1.1em;'><strong>Errores Totales:</strong> <span style='font-weight:bold; color:#dc3545;'>{st.session_state.final_summary_data['total_errors']}</span></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1.1em;'><strong>Dinero Obtenido:</strong> <span style='font-weight:bold; color:#28a745;'>{st.session_state.final_summary_data['money_outcome_description']}</span></p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botón para volver al inicio
    if st.button("Volver al Inicio", help="Haz clic para reiniciar el experimento."):
        initialize_session_state() # Reinicia todo el estado para una nueva sesión
        st.rerun()

