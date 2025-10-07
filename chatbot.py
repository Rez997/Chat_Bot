import logging
import time
import argparse
import random
import json
import re
import os
import pandas as pd
try:
    from sense_hat import SenseHat
    sense = SenseHat()
    SENSE_HAT_AVAILABLE = True
except ImportError:
    SENSE_HAT_AVAILABLE = False


def show_right():
    if not SENSE_HAT_AVAILABLE:
        return
    G = (0, 255, 0)
    O = (0, 0, 0)
    check = [
        O, O, O, O, O, O, O, G,
        O, O, O, O, O, O, G, O,
        O, O, O, O, O, G, O, O,
        G, O, O, O, G, O, O, O,
        O, G, O, G, O, O, O, O,
        O, O, G, O, O, O, O, O,
        O, O, O, O, O, O, O, O,
        O, O, O, O, O, O, O, O,
    ]
    sense.set_pixels(check)
    time.sleep(2)
    sense.clear()

def show_wrong():
    if not SENSE_HAT_AVAILABLE:
     return
    R = (255, 0, 0)
    O = (0, 0, 0)
    cross = [
        R, O, O, O, O, O, O, R,
        O, R, O, O, O, O, R, O,
        O, O, R, O, O, R, O, O,
        O, O, O, R, R, O, O, O,
        O, O, O, R, R, O, O, O,
        O, O, R, O, O, R, O, O,
        O, R, O, O, O, O, R, O,
        R, O, O, O, O, O, O, R,
    ]
    sense.set_pixels(cross)
    time.sleep(2)
    sense.clear()

def show_score(score, total):
     if not SENSE_HAT_AVAILABLE:
      return
     message = f"Score: {score}/{total}"
     sense.show_message(message, scroll_speed=0.08, text_colour=(0, 255, 255))

def show_temperature():
    if not SENSE_HAT_AVAILABLE:
     return
    temp = sense.get_temperature()
    temp = round(temp, 1)
    sense.show_message(f"{temp}C", scroll_speed=0.08, text_colour=(255, 165, 0))

def show_temperature_static():
    if not SENSE_HAT_AVAILABLE:
     return
    temp = sense.get_temperature()
    temp = round(temp, 1)
    # Show as two digits or int part if you prefer
    sense.show_message(f"{int(temp)}C", scroll_speed=0.05, text_colour=(255, 165, 0))

import threading  # make sure this is imported at the top with the others

def scroll_temperature_forever(stop_event):
    if not SENSE_HAT_AVAILABLE:
     return
    """Continuously scrolls temperature until stop_event is set."""
    while not stop_event.is_set():
        temp = sense.get_temperature()
        temp = round(temp, 1)
        sense.show_message(f"{temp}C", scroll_speed=0.08, text_colour=(255, 165, 0))
        # Very short sleep to allow interruption
        time.sleep(0.1)
    sense.clear()


QUESTION_FILE = 'questions.json'

# Default hardcoded questions
questions = {}

stored_questions = {}

question_variants = {
    "what's your name?": "what is your name?",
    "who are you?": "what is your name?",
    "can i know your name?": "what is your name?",
    "how old are you?": "what is your age?",
    "tell me your age?": "what is your age?",
    "where do you stay?": "where do you live?",
    "your location?": "where do you live?",
    "what's your address?": "where do you live?",
    "what do you study in germany?": "what are you study in germany?",
    "what's your major in germany?": "what are you study in germany?",
    "your studies in germany?": "what are you study in germany?",
    "what's the weather like today?": "how is the weather today?",
    "what is today's weather?": "how is the weather today?",
    "weather today?": "how is the weather today?",
    "tell me about python?": "what is python?",
    "describe python?": "what is python?",
    "explain python?": "what is python?",
    "where did you learn python?": "how do you know python?",
    "how did you learn python?": "how do you know python?",
    "is python hard?": "how do you find python language?",
    "what do you think of python?": "how do you find python language?",
    "what can chatbot do?": "what can i do with chatbot?",
    "uses of chatbot?": "what can i do with chatbot?",
    "what info is on chatbot?": "what information are available on chatbot?",
    "what is the location of lecturing hall xxx?": "where is lecturing hall xxx?",
    "where is lecturing hall xxx located?": "where is lecturing hall xxx?",
    "how do i reach lecturing hall xxx?": "where is lecturing hall xxx?"
}

keyword_map = {
    "python": [
        "what is python?",
        "how do you find python language?",
        "how do you know python?"
    ],
    "chatbot": [
        "what can i do with chatbot?",
        "what information are available on chatbot?"
    ],
    "weather": [
        "how is the weather today?"
    ],
    "personal": [
        "what is your name?",
        "what is your age?",
        "where do you live?",
        "what are you study in germany?"
    ],
    "lecture hall": [
        "where is lecturing hall xxx?",
        "what is the location of lecturing hall xxx?",
        "where is lecturing hall xxx located?",
        "how do i reach lecturing hall xxx?"
    ]
    
}
trivia_questions = [
    {
        "question": "What is the name of the university cafeteria at many German universities?",
        "choices": {
            "A": "Mensa",
            "B": "Audimax",
            "C": "Rektorat",
            "D": "Lernzentrum"
        },
        "answer": "A"
    },
    {
        "question": "Ostfalia Hochschule has a campus in which of these cities?",
        "choices": {
            "A": "Munich",
            "B": "Wolfenbüttel",
            "C": "Cologne",
            "D": "Frankfurt"
        },
        "answer": "B"
    },
    {
        "question": "Which card do Ostfalia students use for the library and cafeteria?",
        "choices": {
            "A": "EC-Karte",
            "B": "Girocard",
            "C": "Studentenausweis",
            "D": "Kulturkarte"
        },
        "answer": "C"
    },
    {
        "question": "How can you best check your grades at Ostfalia?",
        "choices": {
            "A": "On a public notice board",
            "B": "Via the Ostfalia web portal",
            "C": "By mail",
            "D": "Ask the Mensa cook"
        },
        "answer": "B"
    },
    {
        "question": "What does the International Office at Ostfalia help with?",
        "choices": {
            "A": "Arranging sports events",
            "B": "Organizing travel for professors",
            "C": "Supporting international students",
            "D": "Serving in the Mensa"
        },
        "answer": "C"
    },
    {
        "question": "Which department would you visit for printing a student transcript?",
        "choices": {
            "A": "Rechenzentrum (IT Office)",
            "B": "Fachschaft",
            "C": "Prüfungsamt (Examination office)",
            "D": "Bibliothek (Library)"
        },
        "answer": "C"
    },
    {
        "question": "During which months does the winter semester at Ostfalia usually start and end?",
        "choices": {
            "A": "June–September",
            "B": "October–March",
            "C": "April–July",
            "D": "January–May"
        },
        "answer": "B"
    },
    {
        "question": "What's the name of the online portal for lectures and course materials?",
        "choices": {
            "A": "OPUS",
            "B": "Zoom",
            "C": "Lernraum",
            "D": "Moodle"
        },
        "answer": "D"
    },
    {
        "question": "Which Ostfalia department helps students find internships?",
        "choices": {
            "A": "Examination Office",
            "B": "Career Service",
            "C": "Library",
            "D": "Sports Office"
        },
        "answer": "B"
    },
    {
        "question": "What do you call the main lecture hall at most German universities?",
        "choices": {
            "A": "Bibliothek",
            "B": "Labor",
            "C": "Audimax",
            "D": "Sekretariat"
        },
        "answer": "C"
    }
]

def current_time():
    return time.strftime("%H:%M:%S")

def format_message(sender, message):
    return f"{current_time()} {sender}: {message}"

def normalize_question(q):
    q = q.lower().strip()
    q = re.sub(r'[?.!]', '', q)
    q = re.sub(r'\s+', ' ', q)
    return q

def parse_args():
    parser = argparse.ArgumentParser(description="Chatbot CLI")

    parser.add_argument("--list-questions", action="store_true",
                        help="List all available questions and exit.")
    parser.add_argument("--question", type=str,
                        help="Ask the chatbot a question from the command line.")
    parser.add_argument("--import_questions", action="store_true",
                        help="Import questions in bulk from a CSV or XLSX file.")
    parser.add_argument("--filetype", type=str, choices=["CSV", "XLSX"],
                        help="Type of import file: CSV or XLSX. Used with --import_questions.")
    parser.add_argument("--filepath", type=str,
                        help="Path to import file when using --import_questions.")
    parser.add_argument("--add", action="store_true",
                        help="Add a new question and answer (requires --question and --answer).")
    parser.add_argument("--remove", action="store_true",
                        help="Remove an answer from a question, or remove a question entirely (requires --question, optional --answer).")
    parser.add_argument("--answer", type=str,
                        help="The answer to add or remove (used with --add or --remove).")
    parser.add_argument("--log", action="store_true", 
                        help="Enable writing actions to chatbot.log file.")
    parser.add_argument("--loglevel", type=str, choices=["INFO", "WARNING"],
                        help="Logging level for chatbot.log (default: WARNING)")

    return parser.parse_args()

def load_questions():
    global stored_questions
    if os.path.exists(QUESTION_FILE):
        with open(QUESTION_FILE, 'r') as f:
            stored_questions = json.load(f)

def save_questions():
    with open(QUESTION_FILE, 'w') as f:
        json.dump(stored_questions, f, indent=2)

def get_all_questions():
    all_q = questions.copy()
    all_q.update(stored_questions)
    return all_q

def add_question(q, a, args):
    
    q = normalize_question(q)
    new_answers = [a] if isinstance(a, str) else a

    if q in stored_questions:
        existing_answers = stored_questions[q]
        for ans in new_answers:
            if ans not in existing_answers:
                existing_answers.append(ans)
        stored_questions[q] = existing_answers
    else:
        stored_questions[q] = new_answers

    save_questions()
    print(f"Updated stored_questions: '{q}' → {stored_questions[q]}")

    # ✅ Add logging here
    if args.log:
        logging.info(f"Added answer '{a}' to question '{q}'")


def remove_answer(question, answer, args):
    q = normalize_question(question)
    if q in stored_questions:
        if answer in stored_questions[q]:
            stored_questions[q].remove(answer)
            # If no answers left, remove the whole question
            if not stored_questions[q]:
                del stored_questions[q]
            save_questions()
            print(f"✅ Answer removed: '{answer}' from question: '{q}'")
            if args.log:
                logging.info(f"Removed answer '{answer}' from question '{q}'")
        else:
            print(f"Answer '{answer}' not found for question '{q}'.")
    else:
        print(f"Question '{q}' not found.")



def remove_question(question, args):
    q = normalize_question(question)
    if q in stored_questions:
        del stored_questions[q]
        save_questions()
        print(f"Removed question '{q}'.")
        if args.log:
            logging.info(f"Removed entire question '{q}'")
    else:
        print(f"Question '{q}' not found.")



def checking_question(compound_question,args):
    all_questions = get_all_questions()
    compound_question = re.sub(r'^(hi|hello|hey)[, ]*', '', compound_question.strip(), flags=re.IGNORECASE)
    split_questions = re.split(r'\?\s*|\band\b|\bor\b', compound_question.lower())
    matched_any = False

    for q in split_questions:
        q = q.strip()
        if not q:
            continue
        nq = normalize_question(q)
        canonical_q = question_variants.get(nq, nq)

        matched_q = None
        for question_key in all_questions:
            if normalize_question(question_key) == canonical_q:
                matched_q = question_key
                break

        if matched_q:
            matched_any = True
            answer = random.choice(all_questions[matched_q])
            print(format_message("Bot", answer))
            if args.log:
                logging.info(f"User asked: '{q}' → Bot answered: '{answer}'")

    if not matched_any:
        print(format_message("Bot", "I have no answer for your question(s)!"))
        if args.log:
            logging.warning(f"Unrecognized question: '{compound_question}'")



def print_trivia_question(qidx):
    q = trivia_questions[qidx]
    print(format_message("Bot", f"\nQ: {q['question']}"))
    for key in sorted(q["choices"].keys()):
        print(f"   {key}. {q['choices'][key]}")
    print(format_message("Bot", "Type A, B, C, or D as your answer:"))

def interactive(args):
    print(format_message("Bot", "Hello! Ask me anything or type a keyword like 'python'. Type 'bye' to exit."))

    state = "idle"
    current_keyword = None
    related_list = []

    # --- Trivia variables ---
    intriviamode = False
    trivia_score = 0
    trivia_current = 0
    trivia_indices = []

    while True:
        stop_event = threading.Event()
        temp_thread = threading.Thread(target=scroll_temperature_forever, args=(stop_event,), daemon=True)
        temp_thread.start()
        user_input = input("You: ").strip().lower()
        stop_event.set()
        temp_thread.join()
        if SENSE_HAT_AVAILABLE:
         sense.clear()

        if user_input == "bye":
            print(format_message("Bot", "Goodbye!"))
            break

   

        # == TRIVIA GAME HANDLING ==
        if user_input == "trivia":
            if not intriviamode:
                # Start new trivia game
                intriviamode = True
                trivia_score = 0
                trivia_current = 0
                trivia_indices = random.sample(range(len(trivia_questions)), min(10, len(trivia_questions)))
                print(format_message("Bot", "🎲 Trivia game activated! Answer the following questions. Type 'score' any time to see your score, or 'trivia' again to stop the game and see your final results."))
                # Ask the first question immediately!
                qidx = trivia_indices[trivia_current]
                print_trivia_question(qidx)
                continue
            else:
                # End trivia, show score, go back to chat
                print(format_message("Bot", f"🏁 Trivia game ended! Your final score: {trivia_score} out of {trivia_current}."))
                intriviamode = False
                continue

        if intriviamode:
            if user_input == "score":
                print(format_message("Bot", f"⭐ Your current score: {trivia_score} out of {trivia_current} attempted."))
                show_score(trivia_score, trivia_current)
                # re-ask the current question (don't increment, repeat same)
                qidx = trivia_indices[trivia_current]
                print_trivia_question(qidx)
                continue

            # Process user's answer to the current question
            qidx = trivia_indices[trivia_current]
            question_info = trivia_questions[qidx]
            correct_answer = question_info["answer"].strip().upper()
            user_answer = user_input.strip().upper()

            trivia_current += 1  # Increment attempted count

            if user_answer == correct_answer:
                trivia_score += 1
                print(format_message("Bot", "✅ Correct!"))
                show_right()
            else:
                print(format_message("Bot", f"❌ Incorrect. The correct answer was: {correct_answer} - {question_info['choices'][correct_answer]}"))
                show_wrong()

            # Next question, or finish the game
            if trivia_current >= len(trivia_indices):
                print(format_message("Bot", f"🏁 Trivia complete! Your final score: {trivia_score} out of {trivia_current}."))
                intriviamode = False
            else:
                qidx = trivia_indices[trivia_current]
                print_trivia_question(qidx)
            continue

        # ========== (existing code below) ==========
        if state == "awaiting_selection" and current_keyword:
            if user_input.isdigit():
                choice = int(user_input) - 1
                if 0 <= choice < len(related_list):
                    selected_question = related_list[choice]
                    normalized_q = normalize_question(selected_question)
                    canonical_q = question_variants.get(normalized_q, normalized_q)
                    all_questions = get_all_questions()

                    matched_q = None
                    for question_key in all_questions:
                        if normalize_question(question_key) == canonical_q:
                            matched_q = question_key
                            break

                    if matched_q:
                        answer = random.choice(all_questions[matched_q])
                        print(format_message("Bot", f"You selected: {selected_question}"))
                        print(format_message("Bot", answer))
                    else:
                        print(format_message("Bot", "Sorry, I don't have an answer for that."))
                    state = "idle"
                    current_keyword = None
                    related_list = []
                else:
                    print(format_message("Bot", "Invalid number. Please try again."))
            else:
                print(format_message("Bot", "Please enter a valid number."))
            continue

        if user_input in keyword_map:
            related_list = keyword_map[user_input]
            current_keyword = user_input
            state = "awaiting_selection"
            print(format_message("Bot", f"Here are related questions about '{user_input}':"))
            for idx, q in enumerate(related_list, 1):
                print(f"{idx}. {q}")
            print(format_message("Bot", "Please enter the number of the question you're interested in."))
        else:
            checking_question(user_input, args)

def list_questions(all_q):
    print("\n--- Canonical Questions ---")
    for i, q in enumerate(all_q.keys(), 1):
        print(f"Q{i}: {q}")

def list_question_variants(variant_dict):
    print("\n--- Question Variants ---")
    for variant, canonical in variant_dict.items():
        print(f"'{variant}' → '{canonical}'")

def import_questions_from_file(filepath, filetype, args):
    try:
        # 1. Check if file exists
        if not os.path.exists(filepath):
            print(f"❌ Error: The file path '{filepath}' does not exist.")
            if args.log:
                logging.warning(f"File path does not exist: '{filepath}'")
            return

        # 2. Check for read permissions
        if not os.access(filepath, os.R_OK):
            print(f"❌ Error: Access denied. Please check file permissions for '{filepath}'.")
            if args.log:
                logging.warning(f"Access denied for file: '{filepath}'")
            return

        # 3. Check file extension
        if filetype.upper() == "CSV" and not filepath.lower().endswith(".csv"):
            print("❌ Error: File type mismatch. Expected a .csv file.")
            if args.log:
                logging.warning("File type mismatch: expected .csv")
            return
        if filetype.upper() == "XLSX" and not filepath.lower().endswith((".xlsx", ".xls")):
            print("❌ Error: File type mismatch. Expected an Excel file (.xlsx or .xls).")
            if args.log:
                logging.warning("File type mismatch: expected .xlsx or .xls")
            return

        # 4. Try reading the file
        if filetype.upper() == "CSV":
            try:
                df = pd.read_csv(filepath)
            except Exception as e:
                print(f"❌ Error reading CSV: {e}")
                if args.log:
                    logging.warning(f"Failed to read CSV: {e}")
                return
        else:
            try:
                df = pd.read_excel(filepath)
            except Exception as e:
                print(f"❌ Error reading Excel file: {e}")
                if args.log:
                    logging.warning(f"Failed to read Excel file: {e}")
                return

        # 5. Normalize columns
        df.columns = df.columns.str.strip().str.lower()

        if 'question' not in df.columns:
            print("❌ Error: Missing required column 'question'.")
            if args.log:
                logging.warning("Missing 'question' column in file.")
            return

        answer_cols = [col for col in df.columns if col.startswith('answer')]
        if not answer_cols:
            print("❌ Error: No 'answer' columns found.")
            if args.log:
                logging.warning("No 'answer' columns found in file.")
            return

        # 6. Process rows
        imported_count = 0
        for _, row in df.iterrows():
            base_q = normalize_question(str(row['question']))
            answers = [str(row[col]).strip() for col in answer_cols if pd.notna(row[col])]
            if answers:
                stored_questions[base_q] = answers
                imported_count += 1

                # Process variations if available
                if 'variations' in df.columns and pd.notna(row['variations']):
                    for var in str(row['variations']).strip().split(';'):
                        var = normalize_question(var)
                        question_variants[var] = base_q

        save_questions()
        print(f"✅ Import successful. {imported_count} question(s) imported.")
        if args.log:
            logging.info(f"Imported {imported_count} question(s) from '{filepath}'.")

    
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        if args.log:
            logging.warning(f"Unexpected error during import: {e}")


    

...

def main():
    global stored_questions
    args = parse_args()
    load_questions()

    # ✅ Setup logging if enabled
    if args.log:
        log_level = logging.WARNING  # default
        if args.loglevel == "INFO":
            log_level = logging.INFO

        logging.basicConfig(
            filename="chatbot.log",
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(message)s",
            filemode="a"  # append mode
        )
        logging.info("🔄 Chatbot started in logging mode.")

    entered_command = False

    if args.add:                                 
        entered_command = True
        if args.question and args.answer:
            add_question(args.question, args.answer, args)
        else:
            print("❌ Error: --add requires both --question and --answer")

    elif args.remove:                            
        entered_command = True
        if args.question and args.answer:
            remove_answer(args.question, args.answer, args)
        elif args.question:
            remove_question(args.question, args)
        else:
            print("❌ Error: --remove requires at least --question")

    elif args.list_questions:                        
        entered_command = True
        list_questions(get_all_questions())
        list_question_variants(question_variants)

    elif args.import_questions and args.filetype and args.filepath:     
        entered_command = True
        import_questions_from_file(args.filepath, args.filetype, args)

    elif args.question and not args.add and not args.remove:            
        entered_command = True
        checking_question(args.question, args)

    if not entered_command:
        interactive(args)

if __name__ == "__main__":
    main()
