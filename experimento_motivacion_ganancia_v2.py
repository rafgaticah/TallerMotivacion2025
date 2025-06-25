import streamlit as st
import random
import time
import pandas as pd # Se mantiene por si hay otras operaciones de datos, aunque no se use para CSV final

# --- Configuración de la página de Streamlit ---
st.set_page_config(layout="centered", page_title="Experimento de Motivación Cognitiva (Ganancia Simplificado)", 
                   initial_sidebar_state="collapsed") # Colapsa el sidebar por defecto

# --- Parámetros del experimento (constantes) ---
SUBTRACT_VALUE = 13
START_NUMBER = 1500  # Nueva tarea: inicia en 1500
TARGET_THRESHOLD = 1400 # Nueva tarea: termina al sobrepasar 1400
MAX_BLOCKS = 4
BLOCK_DURATION = 60  # segundos por bloque
PAUSE_DURATION = 10 # segundos de pausa entre bloques

# --- Inicialización del estado de la sesión de Streamlit ---
def initialize_session_state():
    """Initializes session state variables for the experiment."""
    if 'experiment_phase' not in st.session_state:
        st.session_state.experiment_phase = 'WELCOME'
        st.session_state.group = "Ganancia" # FIJADO A GANANCIA
        st.session_state.initial_money = 100000 # Dinero inicial para el grupo de Ganancia
        st.session_state.current_money = st.session_state.initial_money
        st.session_state.current_block = 0 # 0-indexed, increments when starting block
        st.session_state.current_sequence_number = START_NUMBER # Inicia con el nuevo número
        st.session_state.errors_in_current_block = 0
        st.session_state.feedback_message = ""
        st.session_state.feedback_color = "black"
        st.session_state.block_start_time = 0
        st.session_state.blocks_results = [] # To store results of each block
        st.session_state.block_completed_successfully_counter = 0 
        st.session_state.last_input_value = "" # To control text_input value after submission
        st.session_state.should_autofocus = False # Flag for autofocus
        st.session_state.final_summary_data = {} # To store data for final display

# Call initialization at the start of the script
initialize_session_state()

# --- Navigation and experiment logic functions ---

def next_phase(phase):
    """Cambia la fase del experimento y fuerza un rerender de Streamlit."""
    st.session_state.experiment_phase = phase
    st.rerun() 

def start_experiment_task():
    """Reinicia variables para la tarea principal y comienza el primer bloque."""
    st.session_state.current_money = st.session_state.initial_money
    st.session_state.blocks_results = []
    st.session_state.block_completed_successfully_counter = 0
    st.session_state.current_block = 0 # Reset para asegurar que start_new_block lo incremente a 1
    st.session_state.final_summary_data = {} # Clear summary data for a new run
    start_new_block()

def start_new_block():
    """Inicia un nuevo bloque de la tarea o finaliza el experimento."""
    if st.session_state.current_block < MAX_BLOCKS:
        st.session_state.current_block += 1
        st.session_state.current_sequence_number = START_NUMBER # Inicia con el número nuevo
        st.session_state.errors_in_current_block = 0
        st.session_state.feedback_message = ""
        st.session_state.feedback_color = "black"
        st.session_state.block_start_time = time.time() # Records block start time
        st.session_state.last_input_value = "" # Clears input for new block
        st.session_state.should_autofocus = True # Set flag to autofocus for this new block
        next_phase('EXPERIMENT')
    else:
        # Calcular los datos del resumen final justo antes de pasar a la fase RESULTS
        calculate_and_store_final_summary()
        next_phase('RESULTS')

def handle_block_end(success):
    """
    Manages the end of a block (success or failure), updates money,
    and prepares the next block (or pause).
    """
    block_duration_taken = time.time() - st.session_state.block_start_time
    
    # Check if the block was completed within the time limit
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
        
        # Lógica de Ganancia
        if st.session_state.block_completed_successfully_counter == 1: money_change = 10000
        elif st.session_state.block_completed_successfully_counter == 2: money_change = 20000
        elif st.session_state.block_completed_successfully_counter == 3: money_change = 20000
        elif st.session_state.block_completed_successfully_counter == 4: money_change = 50000
        st.session_state.current_money += money_change
        message_summary = f"¡Ganaste ${money_change:,.0f}!"
        st.session_state.feedback_color = "green"

    else: # Fallido (por error o por tiempo agotado)
        st.session_state.blocks_results.append({
            "block": st.session_state.current_block,
            "success": False,
            "errors": st.session_state.errors_in_current_block,
            "time_taken_s": round(block_duration_taken, 2)
        })
        # En la modalidad de Ganancia, no se pierde dinero por fallar un bloque.
        message_summary = "Bloque no completado a tiempo."
        st.session_state.feedback_color = "red"

        st.session_state.feedback_message = f"Bloque {st.session_state.current_block} no completado. {message_summary}"
    
    st.session_state.current_money = st.session_state.current_money # Force state update
    
    # Check if more blocks remain to introduce pause
    if st.session_state.current_block < MAX_BLOCKS:
        st.session_state.pause_message = f"Fin del Bloque {st.session_state.current_block}. Tómate un breve descanso."
        st.session_state.pause_end_time = time.time() + PAUSE_DURATION
        next_phase('PAUSE_BETWEEN_BLOCKS')
    else:
        # If no more blocks, proceed directly to results
        calculate_and_store_final_summary() # Calcular antes de mostrar resultados
        next_phase('RESULTS')

def process_user_input(user_answer_str):
    """
    Processes the user's answer for the arithmetic task.
    This function is called when the form is submitted.
    """
    
    # 1. First, check if the block time has already expired BEFORE processing the answer.
    if time.time() - st.session_state.block_start_time > BLOCK_DURATION:
        st.session_state.feedback_message = f"¡El tiempo para el Bloque {st.session_state.current_block} se agotó antes de tu respuesta!"
        st.session_state.feedback_color = "orange"
        handle_block_end(False) # Mark block as failed due to timeout
        return # End function here

    # 2. If there's time, process the answer
    try:
        user_answer_int = int(user_answer_str)
        correct_answer_calc = st.session_state.current_sequence_number - SUBTRACT_VALUE

        if user_answer_int == correct_answer_calc:
            st.session_state.current_sequence_number = user_answer_int
            st.session_state.feedback_message = "¡Correcto!"
            st.session_state.feedback_color = "green"
            st.session_state.last_input_value = "" # Clear input if correct
            
            if st.session_state.current_sequence_number <= TARGET_THRESHOLD: # Usa el nuevo umbral
                handle_block_end(True) # Block completed successfully
            else:
                st.rerun() # To update UI with new number and feedback
        else:
            st.session_state.errors_in_current_block += 1
            st.session_state.feedback_message = f"Incorrecto. Reiniciando secuencia desde {START_NUMBER}." # Mensaje actualizado
            st.session_state.feedback_color = "red"
            st.session_state.current_sequence_number = START_NUMBER # Reset sequence to new START_NUMBER
            st.session_state.last_input_value = "" # Clear input on incorrect numeric inputs
            st.rerun()
    except ValueError:
        st.session_state.feedback_message = "Por favor, ingresa un número válido."
        st.session_state.feedback_color = "orange"
        st.session_state.last_input_value = "" # Clear input on non-numeric error
        st.rerun()

# No hay función save_results_to_csv, ya que se eliminó el guardado a CSV.

def calculate_and_store_final_summary():
    """Calculates summary data for final display and stores it in session state."""
    total_errors = sum(block_res['errors'] for block_res in st.session_state.blocks_results)

    learning_coefficient = "N/A" 
    block1_data = next((res for res in st.session_state.blocks_results if res['block'] == 1), None)

    # --- Datos de errores y tiempos para bloques 1, 3, 4 ---
    errors_block1 = "N/A"
    errors_block3 = "N/A"
    errors_block4 = "N/A"
    time_block1_s = "N/A"
    time_block3_s = "N/A"
    time_block4_s = "N/A"

    if block1_data:
        errors_block1 = block1_data['errors']
        if block1_data['success']:
            time_block1_s = f"{block1_data['time_taken_s']:.2f}s"
        else:
            time_block1_s = "No completado"
            
        # Coeficiente de aprendizaje
        block1_errors = block1_data['errors']
        block1_time_s_if_success = block1_data['time_taken_s'] if block1_data['success'] else None

        errors_b3_b4_successful = [
            res['errors'] for res in st.session_state.blocks_results 
            if res['block'] in [3, 4] and res['success']
        ]
        times_b3_b4_successful = [
            res['time_taken_s'] for res in st.session_state.blocks_results 
            if res['block'] in [3, 4] and res['success']
        ]
        
        min_errors_b3_b4 = min(errors_b3_b4_successful) if errors_b3_b4_successful else float('inf')
        min_time_b3_b4_s = min(times_b3_b4_successful) if times_b3_b4_successful else float('inf')

        if block1_errors > 0:
            if min_errors_b3_b4 != float('inf'):
                coefficient_val = (block1_errors - min_errors_b3_b4) / block1_errors
                learning_coefficient = f"{coefficient_val:.2f}"
            else:
                learning_coefficient = "No aplica (sin datos suficientes para comparar mejora de errores en bloques 3 o 4 exitosos)"
        elif block1_errors == 0:
            if block1_data['success'] and block1_time_s_if_success is not None:
                if min_time_b3_b4_s != float('inf') and block1_time_s_if_success > 0:
                    coefficient_val = (block1_time_s_if_success - min_time_b3_b4_s) / block1_time_s_if_success
                    learning_coefficient = f"{coefficient_val:.2f} (basado en tiempo)"
                else:
                    learning_coefficient = "Perfecto (0 errores en Bloque 1, no hay tiempos posteriores exitosos para comparar)"
            else: 
                learning_coefficient = "Perfecto (0 errores en Bloque 1)"
    else:
        learning_coefficient = "N/A (Bloque 1 no completado o datos no disponibles)"

    # Extract errors and times for Block 3 and 4
    for block_res in st.session_state.blocks_results:
        if block_res['block'] == 3:
            errors_block3 = block_res['errors']
            if block_res['success']:
                time_block3_s = f"{block_res['time_taken_s']:.2f}s"
            else:
                time_block3_s = "No completado"
        elif block_res['block'] == 4:
            errors_block4 = block_res['errors']
            if block_res['success']:
                time_block4_s = f"{block_res['time_taken_s']:.2f}s"
            else:
                time_block4_s = "No completado"
    
    money_difference = st.session_state.current_money - st.session_state.initial_money
    money_outcome_description = ""
    if money_difference > 0:
        money_outcome_description = f"Ganancia Total: ${money_difference:,.0f}"
    else: # Solo para el grupo de GANANCIA, se mostraría esto
        money_outcome_description = "No hubo ganancias."


    st.session_state.final_summary_data = {
        "total_errors": total_errors,
        "learning_coefficient": learning_coefficient,
        "money_outcome_description": money_outcome_description,
        "errors_block1": errors_block1,
        "errors_block3": errors_block3,
        "errors_block4": errors_block4,
        "time_block1_s": time_block1_s,
        "time_block3_s": time_block3_s,
        "time_block4_s": time_block4_s,
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
    st.markdown("<p style='color:#666666; font-size:1.2em;'>Este experimento solo cuenta con la modalidad de Evitar Pérdida.</p>", unsafe_allow_html=True) # Mensaje específico
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
                <p style='font-size:1.2em; font-weight:bold; color:#4a235a;'>Estás en el grupo: <span style='color:#dc3545;'>EVITAR PÉRDIDA</span>.</p>
                <p style='color:#333333; font-size:1.05em;'>
                    <span style='font-weight:bold; color:#dc3545;'>Lógica de Penalización:</span><br/>
                    Comienzas con <span style='font-weight:bold;'>${st.session_state.initial_money:,.0f}</span> (ficticios).<br/>
                    Por cada bloque que <span style='font-weight:bold; text-decoration:underline;'>NO</span> completes con éxito (no llegando a {TARGET_THRESHOLD} o menos en el tiempo asignado):<br/>
                    - Primer bloque fallido: pierdes <span style='font-weight:bold;'>$10,000</span>.<br/>
                    - Segundo bloque fallido: pierdes <span style='font-weight:bold;'>$20,000</span> adicionales.<br/>
                    - Tercer bloque fallido: pierdes <span style='font-weight:bold;'>$20,000</span> adicionales.<br/>
                    - Cuarto bloque fallido: pierdes <span style='font-weight:bold;'>$50,000</span> adicionales.<br/>
                    <span style='font-weight:bold;'>Tu objetivo es evitar perder la mayor cantidad de dinero posible.</span>
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
        # Calculate the correct next value for the placeholder
        correct_next_value = st.session_state.current_sequence_number - SUBTRACT_VALUE
        
        user_answer = st.text_input("Ingresa tu respuesta:", 
                                    value=st.session_state.last_input_value, # Retain invalid input value
                                    placeholder=f"El siguiente número es {correct_next_value}", # Suggest correct value
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
                    st.session_state.current_sequence_number = START_NUMBER # Reset sequence to new START_NUMBER
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
    # Calculate summary data only when entering the RESULTS phase for the first time
    if not st.session_state.final_summary_data:
        calculate_and_store_final_summary()

    st.markdown("<h2 style='color:#333333; font-size:2.5em; font-weight:bold;'>Experimento Finalizado</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#666666; font-size:1.2em;'>Tu dinero final es: <span style='color:#dc3545; font-size:1.8em; font-weight:bold;'>${st.session_state.current_money:,.0f}</span></p>", unsafe_allow_html=True) # Color de dinero en rojo para pérdida
    
    st.markdown("<h3 style='color:#333333; font-size:1.8em; font-weight:bold; margin-top:30px;'>Resumen de tu Desempeño:</h3>", unsafe_allow_html=True)

    st.markdown(f"<p style='font-size:1.1em;'><strong>Errores Totales:</strong> <span style='font-weight:bold; color:#dc3545;'>{st.session_state.final_summary_data['total_errors']}</span></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1.1em;'><strong>Resumen Dinero:</strong> <span style='font-weight:bold; color:#dc3545;'>{st.session_state.final_summary_data['money_outcome_description']}</span></p>", unsafe_allow_html=True) # Color de resumen de dinero en rojo
    st.markdown(f"<p style='font-size:1.1em;'><strong>Coeficiente de Aprendizaje (basado en errores):</strong> <span style='font-weight:bold; color:#0056b3;'>{st.session_state.final_summary_data['learning_coefficient']}</span></p>", unsafe_allow_html=True)
    
    # Datos específicos por bloque
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#333333; font-size:1.4em; font-weight:bold;'>Detalle por Bloque:</h4>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1.0em;'><strong>Errores Bloque 1:</strong> {st.session_state.final_summary_data['errors_block1']} (<span style='font-size:0.9em;'>Tiempo: {st.session_state.final_summary_data['time_block1_s']}</span>)</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1.0em;'><strong>Errores Bloque 3:</strong> {st.session_state.final_summary_data['errors_block3']} (<span style='font-size:0.9em;'>Tiempo: {st.session_state.final_summary_data['time_block3_s']}</span>)</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1.0em;'><strong>Errores Bloque 4:</strong> {st.session_state.final_summary_data['errors_block4']} (<span style='font-size:0.9em;'>Tiempo: {st.session_state.final_summary_data['time_block4_s']}</span>)</p>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botón para volver al inicio
    if st.button("Volver al Inicio", help="Haz clic para reiniciar el experimento."):
        # Reinicia todas las variables de sesión
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

