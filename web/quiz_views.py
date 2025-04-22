import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.template.loader import render_to_string

from .forms import (
    QuizForm,
    QuizOptionFormSet,
    QuizQuestionForm,
    QuizQuestionSpecializedForm,
    TakeQuizForm,
)
from .models import Course, Quiz, QuizQuestion, Session, UserQuiz, QuizOption
from .views import course_detail
from .services.AI.ai_model import ai_quiz_corrector

@login_required
def create_course_exam(
    request: HttpRequest, course_id: int | None = None, session_id: int | None = None
) -> HttpResponse:
    """Create a new exam for a course or session."""
    course = None
    session = None

    if course_id:
        course = get_object_or_404(Course, id=course_id)
        # Check if user is the teacher
        if course.teacher != request.user:
            return HttpResponseForbidden("You don't have permission to create exams for this course.")

    if session_id:
        session = get_object_or_404(Session, id=session_id)
        course = session.course
        # Check if user is the teacher
        if course.teacher != request.user:
            return HttpResponseForbidden("You don't have permission to create exams for this session.")

    # Default exam type
    exam_type = "course" if not session else "session"

    # Handle request
    if request.method == "POST":
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.creator = request.user
            quiz.share_code = get_random_string(8)
            quiz.exam_type = exam_type
            quiz.course = course
            quiz.session = session
            quiz.subject = course.subject
            quiz.save()

            messages.success(request, "Exam created successfully. Now add some questions!")
            return redirect("quiz_detail", quiz_id=quiz.id)
    else:
        # Pre-populate form with values from course
        initial_data = {
            "subject": course.subject,
            "time_limit": 60 if exam_type == "session" else 120,
            "title": f"Quiz - {session.title}" if session else f"Final Exam - {course.title}",
            "passing_score": 60,
            "description": f"Quiz for {session.title}" if session else f"Final comprehensive exam for {course.title}",
            "status": "published",
        }
        form = QuizForm(initial=initial_data)

    return render(
        request,
        "web/quiz/quiz_form.html",
        {
            "form": form,
            "title": "Create Session Quiz" if session else "Create Course Exam",
            "course": course,
            "session": session,
            "exam_type": exam_type,
        },
    )


@login_required
def add_question_specialized(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """Add a specialized question to a quiz based on question type."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check if user can edit this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to edit this quiz.")

    # Calculate the next order value
    next_order = 1
    if quiz.questions.exists():
        next_order = quiz.questions.order_by("-order").first().order + 1

    if request.method == "POST":
        form = QuizQuestionSpecializedForm(request.POST, request.FILES)
        # Set the quiz ID explicitly in the form data
        form.instance.quiz_id = quiz.id

        question_type = request.POST.get("question_type")

        # Different handling based on question type
        if question_type in ["multiple", "true_false"]:
            # Use the standard option formset
            formset = QuizOptionFormSet(request.POST, request.FILES, prefix="options")
            formset_valid = formset.is_valid()
        else:
            # No options needed for other question types
            formset = None
            formset_valid = True

        # Validate the form
        form_valid = form.is_valid()

        if form_valid and formset_valid:
            try:
                with transaction.atomic():
                    # Save the question
                    question = form.save(commit=False)
                    question.quiz = quiz
                    question.order = next_order

                    # Handle specialized fields based on question type
                    if question_type == "fill_blank":
                        # Extract the blank parts
                        blank_text = form.cleaned_data.get("text", "")
                        question.text = blank_text
                    elif question_type == "matching":
                        # Get matching items from form
                        items = request.POST.getlist("matching_item[]")
                        matches = request.POST.getlist("matching_match[]")
                        question.matching_items = {
                            "items": items,
                            "matches": matches,
                        }
                    elif question_type == "coding":
                        # Get code starter and expected output
                        question.code_starter = form.cleaned_data.get("code_starter", "")
                        question.expected_output = form.cleaned_data.get("expected_output", "")

                    question.save()

                    # Save options if applicable
                    if formset:
                        formset.instance = question
                        for i, option_form in enumerate(formset):
                            if option_form.cleaned_data and not option_form.cleaned_data.get("DELETE", False):
                                option = option_form.save(commit=False)
                                option.question = question
                                option.order = i
                                option.save()

                messages.success(request, "Question added successfully.")

                # Redirect based on the button clicked
                if "save_and_add" in request.POST:
                    return redirect("add_question_specialized", quiz_id=quiz.id)
                return redirect("quiz_detail", quiz_id=quiz.id)
            except Exception as e:
                print(e)
                # Re-raise the exception
                raise
    else:
        form = QuizQuestionSpecializedForm()
        formset = QuizOptionFormSet(prefix="options")

    return render(
        request,
        "web/quiz/question_specialized_form.html",
        {
            "form": form,
            "formset": formset,
            "quiz": quiz,
            "title": "Add Question",
        },
    )


@login_required
def quiz_list(request):
    """Display a list of quizzes created by the user and quizzes shared with them."""
    user_created_quizzes = Quiz.objects.filter(creator=request.user).order_by("-created_at")

    # Find quizzes shared with this user via attempts
    shared_quizzes = (
        Quiz.objects.filter(user_quizzes__user=request.user)
        .exclude(creator=request.user)
        .distinct()
        .order_by("-created_at")
    )

    # Find public quizzes
    public_quizzes = (
        Quiz.objects.filter(status="published", allow_anonymous=True)
        .exclude(Q(creator=request.user) | Q(id__in=shared_quizzes))
        .order_by("-created_at")[:10]
    )  # Show only 10 recent public quizzes

    context = {
        "user_created_quizzes": user_created_quizzes,
        "shared_quizzes": shared_quizzes,
        "public_quizzes": public_quizzes,
    }

    return render(request, "web/quiz/quiz_list.html", context)


@login_required
def update_quiz(request, quiz_id):
    """Update an existing quiz."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check if user can edit this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to edit this quiz.")

    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, "Quiz updated successfully.")
            return redirect("quiz_detail", quiz_id=quiz.id)
    else:
        form = QuizForm(instance=quiz)

    return render(request, "web/quiz/quiz_form.html", {"form": form, "quiz": quiz, "title": "Edit Quiz"})


@login_required
def quiz_detail(request, quiz_id):
    """Display quiz details, questions, and management options."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check permissions
    is_owner = quiz.creator == request.user
    can_view = is_owner or quiz.status == "published"

    if not can_view:
        return HttpResponseForbidden("You don't have permission to view this quiz.")

    # Get questions with option counts
    questions = quiz.questions.annotate(option_count=Count("options")).order_by("order")

    # Get attempts by this user
    user_attempts = UserQuiz.objects.filter(quiz=quiz, user=request.user).order_by("-start_time")

    # For quiz owners, get overall stats
    if is_owner:
        total_attempts = UserQuiz.objects.filter(quiz=quiz).count()
        average_score = UserQuiz.objects.filter(quiz=quiz).exclude(score=None).values_list("score", flat=True)

        if average_score:
            average_score = sum(average_score) / len(average_score)
        else:
            average_score = 0
    else:
        total_attempts = None
        average_score = None

    context = {
        "quiz": quiz,
        "questions": questions,
        "is_owner": is_owner,
        "user_attempts": user_attempts,
        "total_attempts": total_attempts,
        "average_score": average_score,
        "share_url": request.build_absolute_uri(reverse("quiz_take_shared", kwargs={"share_code": quiz.share_code})),
    }

    return render(request, "web/quiz/quiz_detail.html", context)


@login_required
def add_question(request, quiz_id):
    """Add a question to a quiz."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check if user can edit this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to edit this quiz.")

    # Calculate the next order value
    next_order = 1
    if quiz.questions.exists():
        next_order = quiz.questions.order_by("-order").first().order + 1

    if request.method == "POST":
        form = QuizQuestionForm(request.POST, request.FILES)
        # Set the quiz ID explicitly in the form data
        form.instance.quiz_id = quiz.id
        
        # Handle true/false questions differently
        question_type = request.POST.get('question_type')

        # Handle true/false questions differently
        if form.is_valid() and question_type == 'true_false':
            with transaction.atomic():
                question = form.save(commit=True)
                question.order = next_order
                question.save()
                
                # Create "True" and "False" options
                true_correct = request.POST.get('true_false_answer') == 'true'
                
                # Create or update the "True" option
                true_option = QuizOption(
                    question=question,
                    text="True",
                    is_correct=true_correct,
                    order=0
                )
                true_option.save()
                
                # Create or update the "False" option
                false_option = QuizOption(
                    question=question,
                    text="False",
                    is_correct=not true_correct,
                    order=1
                )
                false_option.save()
                
            messages.success(request, "Question added successfully.")
            return redirect('quiz_detail', quiz_id=quiz.id)
        elif question_type == 'multiple':
            # For other question types, use the formset as before
            formset = QuizOptionFormSet(request.POST, request.FILES, prefix="options")

            if form.is_valid() and formset.is_valid():
                with transaction.atomic():
                    question = form.save(commit=True)
                    question.order = next_order
                    question.save()
                    
                    # Save formset with the question as the instance
                    formset.instance = question
                    formset.save()
                
                # Check if we should redirect to add another question
                if 'save_and_add' in request.POST:
                    return redirect('question_form', quiz_id=quiz.id)

                messages.success(request, "Question added successfully.")
                return redirect('quiz_detail', quiz_id=quiz.id)
        else:
            # Handle short answer questions
            with transaction.atomic():
                question = form.save(commit=True)
                question.order = next_order
                question.save()
                # Get the reference answer
            
            messages.success(request, "Question added successfully.")
            
            if 'save_and_add' in request.POST:
                return redirect('question_form', quiz_id=quiz.id)
            return redirect('quiz_detail', quiz_id=quiz.id)

    else:
        form = QuizQuestionForm(initial={'order': next_order})
        formset = QuizOptionFormSet(prefix="options")

    return render(
        request,
        "web/quiz/question_form.html",
        {
            'form': form,
            'formset': formset,
            'quiz': quiz,
            'question': None,
        }
    )


@login_required
def edit_question(request, question_id):
    """Edit an existing question."""
    question = get_object_or_404(QuizQuestion, id=question_id)
    quiz = question.quiz

    # Check if user can edit this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to edit this question.")

    if request.method == "POST":
        form = QuizQuestionForm(request.POST, request.FILES, instance=question)
        
        question_type = request.POST.get('question_type')
        
        # Handle true/false questions differently
        if question_type == 'true_false':
            if form.is_valid():
                with transaction.atomic():
                    question = form.save(commit=True)
                    
                    true_correct = request.POST.get('true_false_answer') == 'true'

                    # Get or create true/false options
                    true_option, created_true = QuizOption.objects.get_or_create(
                        question=question,
                        text="True",
                        is_correct=true_correct,
                        order=0
                    )
                    true_option.save()

                    false_option, created_false = QuizOption.objects.get_or_create(
                        question=question,
                        text="False",
                        is_correct=not true_correct,
                        order=1
                    )
                    false_option.save()

                    # Delete any other options that might exist
                    QuizOption.objects.filter(question=question).exclude(
                        id__in=[true_option.id, false_option.id]
                    ).delete()
                
                messages.success(request, "Question updated successfully.")
                return redirect("quiz_detail", quiz_id=quiz.id)
        elif question_type == 'multiple':
            # Handle multiple choice questions with formset
            question = form.save(commit=True)

            formset = QuizOptionFormSet(request.POST, request.FILES, instance=question, prefix="options")

            if formset.is_valid():
                formset.save()

            messages.success(request, "Question updated successfully.")
            return redirect("quiz_detail", quiz_id=quiz.id)
        else:
            # Handle short answer questions
            question = form.save(commit=True)

            reference_answer = request.POST.get('short_answer_reference', '')
            
            # First delete existing options
            QuizOption.objects.filter(question=question).delete()
            
            # Create new reference option
            if reference_answer:
                option = QuizOption(
                    question=question,
                    text=reference_answer,
                    is_correct=True,
                    order=0
                )
                option.save()

            messages.success(request, "Question updated successfully.")
            return redirect("quiz_detail", quiz_id=quiz.id)

    else:
        form = QuizQuestionForm(instance=question)
        formset = QuizOptionFormSet(instance=question, prefix="options")

    # Determine which option is correct for true/false questions
    true_is_correct = False
    if question.question_type == 'true_false':
        true_option = question.options.filter(text="True").first()
        if true_option:
            true_is_correct = true_option.is_correct

    return render(
        request,
        'web/quiz/question_form.html',
        {
            'form': form,
            'formset': formset,
            'quiz': quiz,
            'question': question,
            'true_is_correct': true_is_correct,
            "reference_answer": request.POST.get('short_answer_reference', '')
        }
    )


def delete_question(request, question_id):
    """Delete a question from a quiz."""
    question = get_object_or_404(QuizQuestion, id=question_id)
    quiz = question.quiz

    # Check if user can edit this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to delete this question.")

    if request.method == "POST":
        quiz_id = quiz.id
        question.delete()

        # Re-order the remaining questions
        for i, q in enumerate(quiz.questions.order_by("order")):
            q.order = i + 1
            q.save()

        # this message appears after page refresh
        # messages.success(request, "Question deleted successfully.")
        
        # For HTMX requests, return an empty response (removes the element)
        if request.headers.get('HX-Request') == 'true':
            response = HttpResponse('')
            response['HX-Trigger'] = json.dumps({
                "show-toast": {
                    "level": "success",
                    "message": "Question deleted successfully."
                }
            })
            return response

        
        # For regular requests, redirect to the quiz detail page
        return redirect("quiz_detail", quiz_id=quiz_id)

    return render(request, "web/quiz/delete_question.html", {"question": question, "quiz": quiz})


@login_required
def delete_quiz(request, quiz_id):
    """Delete an entire quiz."""
    quiz = Quiz.objects.filter(id=quiz_id).first()

    if not quiz:
        return HttpResponseForbidden("There is no exam with this id.")
    
    # Check if user can delete this quiz
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to delete this quiz.")

    if request.method == "POST":
        quiz.delete()
        messages.success(request, "Quiz deleted successfully.")
        return redirect(course_detail, quiz.course.slug)

    return render(request, "web/quiz/delete_quiz.html", {"quiz": quiz})


def take_quiz_shared(request, share_code):
    """Allow anyone with the share code to take the quiz."""
    quiz = get_object_or_404(Quiz, share_code=share_code)

    # Check if quiz is available
    if quiz.status != "published":
        messages.error(request, "This quiz is not currently available.")
        return redirect("index")

    # Check if anonymous users are allowed
    if not quiz.allow_anonymous and not request.user.is_authenticated:
        messages.error(request, "You must be logged in to take this quiz.")
        return redirect("account_login")

    return _process_quiz_taking(request, quiz)


@login_required
def take_quiz(request, quiz_id):
    """Take a quiz as an authenticated user."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check if quiz is available
    if quiz.status != "published":
        messages.error(request, "This quiz is not currently available.")
        return redirect("quiz_list")

    return _process_quiz_taking(request, quiz)


def _process_quiz_taking(request, quiz):
    """Helper function to process quiz taking for both routes."""
    from .services.AI.ai_model import ai_quiz_corrector

    # Create a new UserQuiz attempt record
    user = request.user if request.user.is_authenticated else None
    user_quiz = UserQuiz(quiz=quiz, user=user)

    # Check if the quiz has questions
    if not quiz.questions.exists():
        messages.error(request, "This quiz does not have any questions yet.")
        return redirect("quiz_list")

    # Get the questions in the correct order
    questions = list(quiz.questions.order_by("order"))

    # Shuffle questions if quiz settings require it
    if quiz.randomize_questions:
        random.shuffle(questions)

    # Check if user has already reached max attempts
    if user and quiz.max_attempts > 0:
        attempt_count = UserQuiz.objects.filter(quiz=quiz, user=user).count()
        if attempt_count >= quiz.max_attempts:
            messages.error(
                request, f"You have reached the maximum number of attempts ({quiz.max_attempts}) for this quiz."
            )
            return redirect("quiz_results", user_quiz_id=user_quiz.id)

    # Prepare questions and options for display
    prepared_questions = []
    for question in questions:
        q_dict = {
            "id": question.id,
            "text": question.text,
            "question_type": question.question_type,
            "explanation": question.explanation,
            "points": question.points,
        }

        # Get options but create new objects that don't have is_correct attribute at all
        options = list(question.options.all())

        # Shuffle options if quiz has option randomization setting
        if quiz.randomize_questions:
            random.shuffle(options)
        # Create plain dictionaries instead of objects to ensure no is_correct data reaches the template
        # This is the most definitive way to prevent any trace of correctness information
        clean_options = []
        for option in options:
            # Only include the minimal data needed for display - deliberately excluding is_correct
            clean_option = {"id": option.id, "text": option.text, "order": option.order}
            clean_options.append(clean_option)

        q_dict["options"] = clean_options
        prepared_questions.append(q_dict)

    if request.method == "POST":
        form = TakeQuizForm(request.POST, quiz=quiz)

        if form.is_valid():
            # Process answers
            quiz_id = quiz.id
            AI_auto_correction = quiz.AI_auto_correction
            answers = {}
            score = 0
            total_points = 0
            correction_status = "not_needed" # Available states: not_needed - pending - in_progress - completed
            ai_correction_results = None

            AI_data = {}
            for question in prepared_questions:
                q_id = str(question["id"])
                question_obj = QuizQuestion.objects.get(id=question["id"])
                total_points += question_obj.points

                user_answer = form.cleaned_data.get(f"question_{q_id}", None)
                User_answer_true_or_false = "Correction needed"
                user_answer_value = None

                if question_obj.question_type == "multiple":
                    '''
                    multiple choice question correction logic:
                    (points/int(corr_ans)) * int(stu_corr_ans) - (points/total_options) * int(Stu_incorr_ans)
                    ''' 

                    user_answers = []
                    for key in request.POST:
                        if key.startswith(f"question_{q_id}_option_"):
                            user_answers.append(key[len(f"question_{q_id}_option_"):] )

                    correct_options = list(
                        question_obj.options.filter(is_correct=True).values_list("id", flat=True)
                    )
                    all_options = question_obj.options.all().values_list("id", flat=True)
                    in_correct_options = len(all_options) - len(correct_options)
                    student_correct_answers = 0
                    student_wrong_answers = 0
                    
                    for option in user_answers:
                        if int(option) in correct_options:
                            student_correct_answers += 1
                        else:
                            student_wrong_answers += 1
                    correct_points = (question_obj.points / len(correct_options)) * student_correct_answers
                    wrong_points = (question_obj.points/in_correct_options) * student_wrong_answers
                    student_score = correct_points - wrong_points

                    User_answer_true_or_false = True if student_score >= (question_obj.points / 2) else False

                    answers[q_id] = {
                        "user_answer": user_answers,
                        "correct_answer": correct_options if correct_options else None,
                        "is_correct": User_answer_true_or_false,
                        "points_awarded": student_score if student_score >= 0 else 0,
                        "is_graded": True,
                    }

                    if student_score >= 0:
                        score += student_score

                elif question_obj.question_type == "true_false":
                    correct_answer = question_obj.options.filter(is_correct=True).first()
                    # For true/false, the view is receiving the option ID, not the text
                    correct_id = str(correct_answer.id) if correct_answer else None

                    User_answer_true_or_false = user_answer == correct_id if user_answer else False

                    if user_answer:
                        user_answer_value = question_obj.options.filter(id=user_answer).first().text

                    answers[q_id] = {
                        "user_answer": user_answer,
                        "correct_answer": correct_id,
                        "is_correct": User_answer_true_or_false,
                        "points_awarded": question_obj.points if User_answer_true_or_false else 0,
                        "is_graded": True,
                    }

                    if answers[q_id]["is_correct"]:
                        score += question_obj.points

                else:
                    correction_status = "in_progress"

                    answers[q_id] = {
                        "user_answer": user_answer,
                        "is_graded": False,  # need manual grading
                    }
                    # correction_status = 'in_progress'

                if str(AI_auto_correction) == "True":
                    AI_data[q_id] = {
                        "question_title": question_obj.text,
                        "question_explanation": question_obj.explanation,
                        "question_max_point": question_obj.points,
                        "question_type": question_obj.question_type,
                        "reference_answer": question_obj.reference_answer,
                        "Student_answer": user_answer_value if user_answer_value is not None else user_answer ,
                        "User_answer_true_or_false": User_answer_true_or_false,
                        "Subject": quiz.subject.name,
                    }

            if str(AI_auto_correction) == "True" and correction_status == "in_progress":
                correction_status = "completed"
                ai_correction_results = json.loads(ai_quiz_corrector(AI_data))

                # Loop through each question in prepared_questions
                for question in prepared_questions:
                    # Extract the question id
                    question_id = str(question.get("id"))

                    # Retrieve corresponding AI data
                    ai_question_data = ai_correction_results.get('correction', {}).get(question_id, '')

                    question_type = AI_data.get(question_id, '').get("question_type", '')
                    answers_question = answers[question_id]

                    if not question_type == "multiple" and not question_type == "true_false":
                        score += ai_question_data["degree"]
                        answers_question["points_awarded"] = ai_question_data["degree"]
                        answers_question["is_graded"] = True
                        answers_question["is_correct"] = True if ai_question_data["degree"] >= question['points'] else False

                    answers_question["student_feedback"] = ai_question_data["student_feedback"]
                    answers_question["teacher_feedback"] = ai_question_data["teacher_feedback"]

            # Update the UserQuiz record
            user_quiz.answers = json.dumps(answers)
            user_quiz.correction_status = correction_status
            user_quiz.score = score
            user_quiz.max_score = total_points
            user_quiz.end_time = timezone.now()
            user_quiz.completed = True
            user_quiz.save()

            # Redirect to results page
            return redirect("quiz_results", user_quiz_id=user_quiz.id)
    else:
        form = TakeQuizForm(quiz=quiz)

    context = {
        "quiz": quiz,
        "questions": prepared_questions,
        "form": form,
        "user_quiz_id": user_quiz.id,
        "quiz_id": quiz.id,
        "user_quiz": user_quiz,
        "time_limit": quiz.time_limit,
    }

    return render(request, "web/quiz/take_quiz.html", context)


def quiz_results(request, user_quiz_id):
    """Display the results of a quiz attempt."""
    user_quiz = get_object_or_404(UserQuiz, id=user_quiz_id)
    quiz = user_quiz.quiz

    # Check permissions
    if user_quiz.user and user_quiz.user != request.user and quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to view these results.")

    # If quiz is still in progress, redirect to take it
    if not user_quiz.completed:
        if quiz.share_code:
            return redirect("quiz_take_shared", share_code=quiz.share_code)
        else:
            return redirect("take_quiz", quiz_id=quiz.id)

    # Parse the answers JSON
    answers = json.loads(user_quiz.answers) if user_quiz.answers else {}

    # Only count questions that have actual answers (not empty or None)
    questions_attempted = 0
    for q_id, ans_data in answers.items():
        # For multiple choice and true/false questions
        if ans_data.get("user_answer") not in [None, "", [], {}]:
            questions_attempted += 1

    correct_count = sum(1 for ans in answers.values() if ans.get("is_correct", False))

    # Calculate duration
    if user_quiz.start_time and user_quiz.end_time:
        duration_seconds = (user_quiz.end_time - user_quiz.start_time).total_seconds()
        minutes, seconds = divmod(int(duration_seconds), 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            duration = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            duration = f"{minutes}m {seconds}s"
        else:
            duration = f"{seconds}s"
    else:
        duration = "N/A"

    # Update quiz completion status and score
    user_quiz.completed = True
    user_quiz.end_time = timezone.now()  # Ensure end_time is set if not already
    user_quiz.save()

    # Check if this quiz is associated with a challenge
    challenge_invitation = None
    if request.user.is_authenticated:
        from .models import PeerChallengeInvitation

        # First try to find an invitation that's already associated with this user_quiz
        challenge_invitation = PeerChallengeInvitation.objects.filter(
            user_quiz=user_quiz, participant=request.user
        ).first()

        # If not found, look for an invitation for this quiz
        if not challenge_invitation:
            challenge_invitation = PeerChallengeInvitation.objects.filter(
                participant=request.user, challenge__quiz=quiz
            ).first()

    # Get user attempts count for this quiz
    user_attempts = 0
    if request.user.is_authenticated:
        user_attempts = UserQuiz.objects.filter(quiz=quiz, user=request.user).count()

    # Get all questions for the quiz to display in the questions section
    all_questions = quiz.questions.order_by("order")
    total_questions = 0
    for question in all_questions:
        total_questions += 1
        id = str(question.id)
        options = question.options.all()

        answers[id]["question_title"] = question.text
        answers[id]["type_display"] =  question.get_question_type_display()
        answers[id]["question_type"] = question.question_type
        answers[id]["options"] = options
        answers[id]["original_points"] = question.points

    context = {
        "user_quiz": user_quiz,
        "show_answers": quiz.creator == request.user,
        "is_owner": user_quiz.user == request.user,
        "is_creator": quiz.creator == request.user,
        "total_questions": total_questions,
        "questions_attempted": questions_attempted,
        "correct_count": correct_count,
        "duration": duration,
        "answers": answers,
        "user_attempts": user_attempts,
    }
    return render(request, "web/quiz/quiz_results.html", context)


@login_required
def grade_short_answer(request, user_quiz_id, question_id):
    """Allow quiz creator to grade short answer questions."""
    user_quiz = get_object_or_404(UserQuiz, id=user_quiz_id)
    question = get_object_or_404(QuizQuestion, id=question_id)

    # Check permissions
    if question.quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to grade this answer.")

    if request.method == "POST":
        # Get the points awarded
        points_awarded = float(request.POST.get("points_awarded", 0))
        if points_awarded < 0:
            points_awarded = 0
        if points_awarded > question.points:
            points_awarded = question.points

        # Update the answers JSON
        answers = json.loads(user_quiz.answers) if user_quiz.answers else {}
        q_id = str(question.id)

        if q_id in answers:
            answers[q_id]["is_graded"] = True
            answers[q_id]["points_awarded"] = points_awarded
            answers[q_id]["is_correct"] = points_awarded == question.points

            # Calculate new total score
            total_points = sum(q.points for q in user_quiz.quiz.questions.all())
            current_score = sum(
                (
                    answers.get(str(q.id), {}).get("points_awarded", 0)
                    if answers.get(str(q.id), {}).get("is_graded", False)
                    else (question.points if answers.get(str(q.id), {}).get("is_correct", False) else 0)
                )
                for q in user_quiz.quiz.questions.all()
            )

            # Update the UserQuiz record
            user_quiz.answers = json.dumps(answers)
            user_quiz.score = (current_score / total_points * 100) if total_points > 0 else 0
            user_quiz.save()

            messages.success(
                request, f"Answer graded successfully. Awarded {points_awarded} out of {question.points} points."
            )

        return redirect("quiz_results", user_quiz_id=user_quiz.id)

    # Get the current answer
    answers = json.loads(user_quiz.answers) if user_quiz.answers else {}
    q_id = str(question.id)
    answer = answers.get(q_id, {}).get("user_answer", "")

    context = {
        "user_quiz": user_quiz,
        "question": question,
        "answer": answer,
    }

    return render(request, "web/quiz/grade_short_answer.html", context)


@login_required
def quiz_analytics(request, quiz_id):
    """Show detailed analytics for a quiz creator."""
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check permissions
    if quiz.creator != request.user:
        return HttpResponseForbidden("You don't have permission to view analytics for this quiz.")

    # Get all attempts
    attempts = UserQuiz.objects.filter(quiz=quiz, completed=True).order_by("-end_time")

    # Calculate overall statistics
    total_attempts = attempts.count()
    average_score = attempts.exclude(score=None).values_list("score", flat=True)
    if average_score:
        average_score = sum(average_score) / len(average_score)
    else:
        average_score = 0

    # Calculate pass rate
    pass_count = attempts.filter(score__gte=quiz.passing_score).count()
    pass_rate = (pass_count / total_attempts * 100) if total_attempts > 0 else 0

    # We're not using JavaScript calculation anymore, so we don't need to prepare timing data

    # Calculate average time on the server side
    avg_time_seconds = 0
    time_tracking_attempts = 0

    for attempt in attempts:
        if attempt.start_time and attempt.end_time:
            duration = (attempt.end_time - attempt.start_time).total_seconds()
            if 0 < duration < 24 * 60 * 60:  # Exclude outliers (more than a day)
                avg_time_seconds += duration
                time_tracking_attempts += 1

    if time_tracking_attempts > 0:
        avg_time_seconds = avg_time_seconds / time_tracking_attempts
        minutes, seconds = divmod(int(avg_time_seconds), 60)
        hours, minutes = divmod(minutes, 60)

        # Format the average time in a user-friendly way
        if hours > 0:
            avg_time = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            avg_time = f"{minutes}m {seconds}s"
        else:
            avg_time = f"{seconds}s"  # Always show seconds even if it's 0
    else:
        avg_time = "N/A"

    # Analyze performance by question
    questions = quiz.questions.all()
    question_stats = {}

    for question in questions:
        question_stats[question.id] = {
            "text": question.text,
            "correct_count": 0,
            "attempt_count": 0,
            "success_rate": 0,
            "type": question.question_type,
        }

    for attempt in attempts:
        if not attempt.answers:
            continue

        answers = json.loads(attempt.answers)
        for q_id, answer_data in answers.items():
            q_id = int(q_id)
            if q_id in question_stats:
                question_stats[q_id]["attempt_count"] += 1
                if answer_data.get("is_correct", False):
                    question_stats[q_id]["correct_count"] += 1

    # Calculate success rates
    for q_id in question_stats:
        stats = question_stats[q_id]
        if stats["attempt_count"] > 0:
            stats["success_rate"] = (stats["correct_count"] / stats["attempt_count"]) * 100
            stats["correct_rate"] = stats["success_rate"]  # For template compatibility

    # Get user performance statistics
    user_performances = []
    user_attempt_dict = {}

    for attempt in attempts:
        user_id = attempt.user.id
        if user_id not in user_attempt_dict:
            user_attempt_dict[user_id] = {
                "user": attempt.user,
                "attempts": 0,
                "best_score": attempt.calculate_score(),
                "total_score": 0,
            }

        user_data = user_attempt_dict[user_id]
        user_data["attempts"] += 1
        if attempt.score is not None:
            user_data["total_score"] += attempt.calculate_score()
            if attempt.calculate_score() > user_data["best_score"]:
                user_data["best_score"] = attempt.calculate_score()

    for user_id, data in user_attempt_dict.items():
        if data["attempts"] > 0:
            data["avg_score"] = data["total_score"] / data["attempts"]
            user_performances.append(data)

    # Sort by best score
    user_performances.sort(key=lambda x: x["best_score"], reverse=True)

    # Score distribution data for chart
    score_ranges = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0,
    }

    for attempt in attempts:
        if attempt.score is not None:
            if attempt.score <= 20:
                score_ranges["0-20"] += 1
            elif attempt.score <= 40:
                score_ranges["21-40"] += 1
            elif attempt.score <= 60:
                score_ranges["41-60"] += 1
            elif attempt.score <= 80:
                score_ranges["61-80"] += 1
            else:
                score_ranges["81-100"] += 1

    # Prepare chart data in the format expected by the template
    # Score distribution data for chart
    score_distribution = {"labels": list(score_ranges.keys()), "data": list(score_ranges.values())}

    # Question performance data
    question_performance = {
        "labels": [f"Q{i + 1}" for i, q in enumerate(question_stats.values())],
        "data": [q["success_rate"] for q in question_stats.values()],
    }

    # Time chart data - attempts over time by month
    time_data = {}
    for attempt in attempts:
        if attempt.end_time:
            month_year = attempt.end_time.strftime("%b %Y")
            if month_year in time_data:
                time_data[month_year] += 1
            else:
                time_data[month_year] = 1

    # If no data, provide at least one month
    if not time_data:
        current_month = timezone.now().strftime("%b %Y")
        time_data[current_month] = 0

    time_chart = {"labels": list(time_data.keys()), "data": list(time_data.values())}

    # Preprocess recent attempts to ensure duration is calculated
    recent_attempts = attempts[:20]  # Limit to 20 most recent attempts
    for attempt in recent_attempts:
        # Explicitly set time_taken for display in template
        if attempt.start_time and attempt.end_time:
            duration_seconds = (attempt.end_time - attempt.start_time).total_seconds()
            if duration_seconds < 60:
                attempt.time_taken = f"{int(duration_seconds)}s"
            else:
                minutes, seconds = divmod(int(duration_seconds), 60)
                if minutes < 60:
                    attempt.time_taken = f"{minutes}m {seconds}s"
                else:
                    hours, minutes = divmod(minutes, 60)
                    attempt.time_taken = f"{hours}h {minutes}m {seconds}s"
        else:
            attempt.time_taken = "N/A"

    # Create context with all required data
    context = {
        "quiz": quiz,
        "total_attempts": total_attempts,
        "avg_score": average_score,
        "pass_rate": pass_rate,
        "avg_time": avg_time,  # Server-side calculation
        "question_analysis": [stats for stats in question_stats.values()],
        "question_stats": question_stats,
        "recent_attempts": recent_attempts,
        "user_performances": user_performances[:10],  # Top 10 performers
        "score_distribution": score_distribution,
        "question_performance": question_performance,
        "time_chart": time_chart,
    }

    # All context variables are set correctly

    return render(request, "web/quiz/quiz_analytics.html", context)


@login_required
def student_exam_correction(
    request: HttpRequest,
    course_id: int,
    quiz_id: int,
    user_quiz_id: int,
) -> HttpResponse:
    """View and grade a specific student's exam"""
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    user_quiz = get_object_or_404(UserQuiz, id=user_quiz_id, quiz=quiz)

    # Check if user is the teacher
    if course.teacher != request.user:
        return HttpResponseForbidden("You don't have permission to grade exams for this course.")

    # Check if the exam is completed
    if not user_quiz.completed:
        messages.error(request, "This exam is not completed yet.")
        # return redirect('course_exam_analytics', course_id=course.id)
        return quiz_analytics(request, course_id=course.id)

    # Parse answers JSON
    answers = json.loads(user_quiz.answers) if user_quiz.answers else {}

    # If user is submitting a grade
    if request.method == "POST":
        # Get question ID and points from POST data
        question_id = request.POST.get("question_id")
        points_awarded = float(request.POST.get("points_awarded", 0))

        # Get the question
        question = quiz.questions.filter(id=question_id).first()

        if question:
            # Validate points
            if points_awarded < 0:
                points_awarded = 0
            if points_awarded > question.points:
                points_awarded = question.points

            # Update the answer
            if question_id in answers:
                answers[question_id]["is_graded"] = True
                answers[question_id]["points_awarded"] = points_awarded
                answers[question_id]["is_correct"] = True if points_awarded >= (question.points / 2) else False

                current_score = 0

                for q in quiz.questions.all():
                    q_id = str(q.id)
                    if q_id in answers:
                        current_score += answers[q_id].get("points_awarded", 0)

                # Update user quiz
                user_quiz.answers = json.dumps(answers)
                user_quiz.score = current_score if current_score > 0 else 0

                # Check if all questions are graded
                all_graded = True
                for q in quiz.questions.all():
                    q_id = str(q.id)
                    if (
                        q_id in answers
                        and not answers[q_id].get("is_graded", False)
                        and not answers[q_id].get("is_correct", False)
                    ):
                        all_graded = False
                        break

                if all_graded:
                    user_quiz.correction_status = "completed"
                else:
                    user_quiz.correction_status = "in_progress"

                user_quiz.save()

                # Check if this is an HTMX request
                if request.headers.get('HX-Request') == 'true':
                    html = render_to_string("web/quiz/partials/graded_info.html", {
                        "question": question,
                        "quiz": quiz,
                        "user_quiz": user_quiz,
                        "points_awarded": points_awarded,
                        "half_question_points": (question.points / 2),
                    }, request=request)

                    response = HttpResponse(html)
                    response["HX-Trigger"] = json.dumps({
                        "show-toast": {
                            "level": "success",
                            "message": "Grade saved successfully."
                        }
                    })
                    return response

    # Prepare questions and answers for display
    questions = []
    for question in quiz.questions.all():
        q_dict = {
            "id": question.id,
            "text": question.text,
            "question_type": question.question_type,
            "points": question.points,
            "explanation": question.explanation,
        }

        # Get options if applicable
        if question.question_type in ["multiple", "true_false"]:
            q_dict["options"] = list(question.options.all())

        # Get user's answer
        q_id = str(question.id)
        if q_id in answers:
            answer_data = answers[q_id]
            q_dict["user_answer"] = answer_data.get("user_answer", "")
            q_dict["is_correct"] = answer_data.get("is_correct", False)
            q_dict["is_graded"] = answer_data.get("is_graded", False)
            q_dict["points_awarded"] = answer_data.get("points_awarded", 0)
            q_dict["options"] = list(question.options.all())
            q_dict["needs_grading"] = question.question_type not in ["multiple", "true_false"] and not answer_data.get(
                "is_graded",
                False,
            )
        else:
            q_dict["user_answer"] = ""
            q_dict["is_correct"] = False
            q_dict["is_graded"] = False
            q_dict["points_awarded"] = 0
            q_dict["needs_grading"] = False

        questions.append(q_dict)

    return render(
        request,
        "web/quiz/student_exam_correction.html",
        {
            "course": course,
            "quiz": quiz,
            "user_quiz": user_quiz,
            "questions": questions,
            "student": user_quiz.user,
            "attempt": user_quiz,
        },
    )
