from __future__ import annotations
from enum import Enum
from pydantic import BaseModel
from pydantic import Field
from pydantic import UUID4
from pydantic.types import StringConstraints
from typing import Annotated
from typing import Any
from typing import Any
from pydantic import Json
import datetime


# ENUM TYPES
# These are generated from Postgres user-defined enum types.

class PublicProductTypeEnumEnum(str, Enum):
	QGEN = "qgen"
	AI_TUTOR = "ai_tutor"

class PublicQuestionTypeEnumEnum(str, Enum):
	MCQ4 = "mcq4"
	MSQ4 = "msq4"
	SHORT_ANSWER = "short_answer"
	TRUE_OR_FALSE = "true_or_false"
	FILL_IN_THE_BLANKS = "fill_in_the_blanks"
	LONG_ANSWER = "long_answer"
	MATCH_THE_FOLLOWING = "match_the_following"

class PublicHardnessLevelEnumEnum(str, Enum):
	EASY = "easy"
	MEDIUM = "medium"
	HARD = "hard"



# CUSTOM CLASSES
# Note: These are custom model classes for defining common features among
# Pydantic Base Schema.


class CustomModel(BaseModel):
	"""Base model class with common features."""
	pass


class CustomModelInsert(CustomModel):
	"""Base model for insert operations with common features."""
	pass


class CustomModelUpdate(CustomModel):
	"""Base model for update operations with common features."""
	pass


# BASE CLASSES
# Note: These are the base Row models that include all fields.


class ActivitiesBaseSchema(CustomModel):
	"""Activities Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	created_at: datetime.datetime
	name: str
	product_type: PublicProductTypeEnumEnum
	updated_at: datetime.datetime
	user_id: UUID4


class BankQuestionsBaseSchema(CustomModel):
	"""BankQuestions Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	answer_text: str
	chapter_id: UUID4 | None = Field(default=None)
	correct_mcq_option: int | None = Field(default=None)
	created_at: datetime.datetime
	explanation: str | None = Field(default=None)
	figure: str | None = Field(default=None)
	hardness_level: PublicHardnessLevelEnumEnum | None = Field(default=None)
	is_from_exercise: bool = Field(description="1 if from exercise of the textbook, 0 otherwise")
	is_image_needed: bool = Field(description="1 if image is to be inserted yet for the question, 0 otherwise")
	is_incomplete: bool = Field(description="1 if any manual modifications are needed or any errors are there in the question, 0 otherwise")
	is_solved_example: bool = Field(description="1 if it is solved example from the textbook, 0 otherwise")
	is_true: bool | None = Field(default=None, description="This is the answer of the true or false question if present")
	marks: int | None = Field(default=None)
	match_columns: str | None = Field(default=None, description="Columns for the match the following question")
	msq_option1_answer: bool | None = Field(default=None)
	msq_option2_answer: bool | None = Field(default=None)
	msq_option3_answer: bool | None = Field(default=None)
	msq_option4_answer: bool | None = Field(default=None)
	option1: str | None = Field(default=None)
	option2: str | None = Field(default=None)
	option3: str | None = Field(default=None)
	option4: str | None = Field(default=None)
	question_text: str
	question_type: PublicQuestionTypeEnumEnum
	reference: str | None = Field(default=None)
	subject_id: UUID4
	svgs: str | None = Field(default=None, description="SVGs as text, if exists any")
	updated_at: datetime.datetime | None = Field(default=None)


class BankQuestionsConceptsMapsBaseSchema(CustomModel):
	"""BankQuestionsConceptsMaps Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	bank_question_id: UUID4
	concept_id: UUID4
	created_at: datetime.datetime


class BoardsBaseSchema(CustomModel):
	"""Boards Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	created_at: datetime.datetime
	description: str | None = Field(default=None)
	name: str
	updated_at: datetime.datetime


class ChaptersBaseSchema(CustomModel):
	"""Chapters Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	created_at: datetime.datetime
	description: str | None = Field(default=None)
	name: str
	position: str
	subject_id: UUID4
	updated_at: datetime.datetime


class ConceptsBaseSchema(CustomModel):
	"""Concepts Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	created_at: datetime.datetime
	description: str | None = Field(default=None)
	name: str
	page_number: int
	topic_id: UUID4
	updated_at: datetime.datetime


class ConceptsActivitiesMapsBaseSchema(CustomModel):
	"""ConceptsActivitiesMaps Base Schema."""

	# Primary Keys
	id: int

	# Columns
	activity_id: UUID4 | None = Field(default=None)
	concept_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime


class GenArtifactsBaseSchema(CustomModel):
	"""GenArtifacts Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	activity_id: UUID4
	created_at: datetime.datetime
	name: str
	source_url: str
	updated_at: datetime.datetime


class GenImagesBaseSchema(CustomModel):
	"""GenImages Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	created_at: datetime.datetime
	file_path: str | None = Field(default=None)
	gen_question_id: UUID4 | None = Field(default=None)
	img_url: str | None = Field(default=None)
	position: int | None = Field(default=None)
	svg_string: str | None = Field(default=None)


class GenQuestionVersionsBaseSchema(CustomModel):
	"""GenQuestionVersions Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	answer_text: str
	correct_mcq_option: int | None = Field(default=None)
	created_at: datetime.datetime
	explanation: str | None = Field(default=None)
	gen_question_id: UUID4 | None = Field(default=None)
	hardness_level: PublicHardnessLevelEnumEnum
	is_active: bool
	is_deleted: bool
	marks: int
	match_the_following_columns: dict | list[dict] | list[Any] | Json | None = Field(default=None)
	msq_option1_answer: bool | None = Field(default=None)
	msq_option2_answer: bool | None = Field(default=None)
	msq_option3_answer: bool | None = Field(default=None)
	msq_option4_answer: bool | None = Field(default=None)
	option1: str | None = Field(default=None)
	option2: str | None = Field(default=None)
	option3: str | None = Field(default=None)
	option4: str | None = Field(default=None)
	question_text: str | None = Field(default=None)
	question_type: PublicQuestionTypeEnumEnum
	version_index: int


class GenQuestionsBaseSchema(CustomModel):
	"""GenQuestions Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	activity_id: UUID4
	answer_text: str = Field(description="Answer for the Generated question. Not For MCQs and MSQs")
	correct_mcq_option: int | None = Field(default=None, description="can be 1 or 2 or 3 or 4")
	created_at: datetime.datetime
	explanation: str | None = Field(default=None, description="explanation for the question and answer")
	hardness_level: PublicHardnessLevelEnumEnum
	is_exercise_question: bool = Field(description="1 if the question is pushed here from the bank question table where is_exercise_question  was true")
	is_in_draft: bool
	is_new: bool
	is_page_break_below: bool = Field(description="If the question is in a draft, then this variable will tell if to add a page break after this question in the pdf being generated")
	is_solved_example: bool = Field(description="1 if the question is pushed here from the bank question table where is_solved_example was true")
	marks: int
	match_the_following_columns: dict | list[dict] | list[Any] | Json | None = Field(default=None)
	msq_option1_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	msq_option2_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	msq_option3_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	msq_option4_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	option1: str | None = Field(default=None, description="For MCQ or MSQs")
	option2: str | None = Field(default=None, description="For MCQs or MSQs")
	option3: str | None = Field(default=None, description="For MCQs or MSQs")
	option4: str | None = Field(default=None, description="For MCQs or MSQs")
	position_in_draft: int | None = Field(default=None, description="Position of the question in the section in the draft, if this question belongs to a draft")
	qgen_draft_section_id: UUID4 | None = Field(default=None, description="The id of the section to which this question belongs to if, this is in draft")
	question_text: str | None = Field(default=None, description="Actual Question")
	question_type: PublicQuestionTypeEnumEnum
	updated_at: datetime.datetime


class GenQuestionsConceptsMapsBaseSchema(CustomModel):
	"""GenQuestionsConceptsMaps Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	concept_id: UUID4
	created_at: datetime.datetime
	gen_question_id: UUID4


class GenerationPaneConceptsMapsBaseSchema(CustomModel):
	"""GenerationPaneConceptsMaps Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	concept_id: UUID4
	created_at: datetime.datetime
	qgen_generation_pane_id: UUID4


class OrgsBaseSchema(CustomModel):
	"""Orgs Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	address: str | None = Field(default=None)
	board_id: UUID4 | None = Field(default=None, description="To which board the organisation belongs to")
	created_at: datetime.datetime
	email: str
	header_line: str | None = Field(default=None)
	logo_url: str | None = Field(default=None)
	org_type: str | None = Field(default=None)
	phone_num: str
	updated_at: datetime.datetime


class PhonenumOtpsBaseSchema(CustomModel):
	"""PhonenumOtps Base Schema."""

	# Primary Keys
	phone_number: str

	# Columns
	created_at: datetime.datetime
	otp: str


class QgenDraftInstructionsDraftsMapsBaseSchema(CustomModel):
	"""QgenDraftInstructionsDraftsMaps Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	created_at: datetime.datetime
	instruction_text: str | None = Field(default=None)
	qgen_draft_id: UUID4
	updated_at: datetime.datetime | None = Field(default=None)


class QgenDraftSectionsBaseSchema(CustomModel):
	"""QgenDraftSections Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	created_at: datetime.datetime
	position_in_draft: int = Field(description="The position of the section in the draft of the paper to be generated as PDF")
	qgen_draft_id: UUID4 | None = Field(default=None)
	section_name: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class QgenDraftsBaseSchema(CustomModel):
	"""QgenDrafts Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	activity_id: UUID4
	created_at: datetime.datetime
	institute_name: str | None = Field(default=None, description="Institute / School Name to be shown on the top of the generated pdf of the paper")
	logo_url: str | None = Field(default=None, description="URL of the logo to be shown on the generated question paper pdf")
	max_position: int | None = Field(default=None)
	maximum_marks: int | None = Field(default=None, description="Maximum / Total Marks to be shown on the generated paper PDF")
	paper_datetime: datetime.datetime | None = Field(default=None, description="The Date and time of examination to be shown on the generated PDF")
	paper_duration: datetime.time | None = Field(default=None, description="Duration of the paper to be shown on the generated PDF")
	paper_subtitle: str | None = Field(default=None, description="Subtitle of the paper to be shown in the generated pdf")
	paper_title: str | None = Field(default=None, description="Title of the Paper to be shown in the generated PDF")
	school_class_name: str | None = Field(default=None)
	subject_name: str | None = Field(default=None)
	updated_at: datetime.datetime


class QgenGenerationPanesBaseSchema(CustomModel):
	"""QgenGenerationPanes Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	activity_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime
	custom_instructions: str | None = Field(default=None)
	difficulty_level_easy_count: int | None = Field(default=None)
	difficulty_level_hard_count: int | None = Field(default=None)
	difficulty_level_medium_count: int | None = Field(default=None)
	exercise_questions_count: int | None = Field(default=None)
	fill_in_the_blanks_count: int | None = Field(default=None)
	long_answer_count: int | None = Field(default=None)
	match_the_following_count: int | None = Field(default=None)
	mcq_count: int | None = Field(default=None)
	msq_count: int | None = Field(default=None)
	school_class_id: UUID4 | None = Field(default=None)
	short_answer_count: int | None = Field(default=None)
	solved_examples_count: int | None = Field(default=None)
	subject_id: UUID4 | None = Field(default=None)
	total_marks_count: int | None = Field(default=None)
	total_time_count: int | None = Field(default=None)
	true_false_count: int | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class SchoolClassesBaseSchema(CustomModel):
	"""SchoolClasses Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	board_id: UUID4
	created_at: datetime.datetime
	description: str | None = Field(default=None)
	name: str
	position: int
	updated_at: datetime.datetime


class SubjectsBaseSchema(CustomModel):
	"""Subjects Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	created_at: datetime.datetime
	description: str | None = Field(default=None)
	name: str
	school_class_id: UUID4
	updated_at: datetime.datetime


class TopicsBaseSchema(CustomModel):
	"""Topics Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	chapter_id: UUID4
	created_at: datetime.datetime
	description: str | None = Field(default=None)
	name: str
	position: str
	updated_at: datetime.datetime


class UsersBaseSchema(CustomModel):
	"""Users Base Schema."""

	# Primary Keys
	id: UUID4

	# Columns
	account_status: str = Field(description="Is account active or disabled or inactive or deactivated etc.")
	avatar_url: str | None = Field(default=None)
	created_at: datetime.datetime
	credits: int
	email: str | None = Field(default=None)
	is_test_user: bool
	last_active_at: datetime.datetime = Field(description="To track user Churn")
	name: Annotated[str, StringConstraints(**{'max_length': 50})] | None = Field(default=None, description="The Full Name of The User")
	org_id: UUID4 | None = Field(default=None)
	phone_num: str | None = Field(default=None)
	updated_at: datetime.datetime
	user_entered_school_address: str | None = Field(default=None, description="The School Address which user manually enters, for thus who are not associated with any organisation")
	user_entered_school_board: str | None = Field(default=None, description="The Board which user enters manually, for thus users who are not part of any organisation, and doing a signup via website directly.")
	user_entered_school_name: str | None = Field(default=None, description="The School Name which the User have Entered, for direct login users, not associated with organisation initially")
	user_type: str
# INSERT CLASSES
# Note: These models are used for insert operations. Auto-generated fields
# (like IDs and timestamps) are optional.


class ActivitiesInsert(CustomModelInsert):
	"""Activities Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# updated_at: has default value
	
	# Required fields
	name: str
	product_type: PublicProductTypeEnumEnum
	user_id: UUID4
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class BankQuestionsInsert(CustomModelInsert):
	"""BankQuestions Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# chapter_id: nullable
	# correct_mcq_option: nullable
	# created_at: has default value
	# explanation: nullable
	# figure: nullable
	# hardness_level: nullable, has default value
	# is_from_exercise: has default value
	# is_image_needed: has default value
	# is_incomplete: has default value
	# is_solved_example: has default value
	# is_true: nullable
	# marks: nullable
	# match_columns: nullable
	# msq_option1_answer: nullable
	# msq_option2_answer: nullable
	# msq_option3_answer: nullable
	# msq_option4_answer: nullable
	# option1: nullable
	# option2: nullable
	# option3: nullable
	# option4: nullable
	# reference: nullable
	# svgs: nullable
	# updated_at: nullable, has default value
	
	# Required fields
	answer_text: str
	question_text: str
	question_type: PublicQuestionTypeEnumEnum
	subject_id: UUID4
	
		# Optional fields
	chapter_id: UUID4 | None = Field(default=None)
	correct_mcq_option: int | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	explanation: str | None = Field(default=None)
	figure: str | None = Field(default=None)
	hardness_level: PublicHardnessLevelEnumEnum | None = Field(default=None)
	is_from_exercise: bool | None = Field(default=None, description="1 if from exercise of the textbook, 0 otherwise")
	is_image_needed: bool | None = Field(default=None, description="1 if image is to be inserted yet for the question, 0 otherwise")
	is_incomplete: bool | None = Field(default=None, description="1 if any manual modifications are needed or any errors are there in the question, 0 otherwise")
	is_solved_example: bool | None = Field(default=None, description="1 if it is solved example from the textbook, 0 otherwise")
	is_true: bool | None = Field(default=None, description="This is the answer of the true or false question if present")
	marks: int | None = Field(default=None)
	match_columns: str | None = Field(default=None, description="Columns for the match the following question")
	msq_option1_answer: bool | None = Field(default=None)
	msq_option2_answer: bool | None = Field(default=None)
	msq_option3_answer: bool | None = Field(default=None)
	msq_option4_answer: bool | None = Field(default=None)
	option1: str | None = Field(default=None)
	option2: str | None = Field(default=None)
	option3: str | None = Field(default=None)
	option4: str | None = Field(default=None)
	reference: str | None = Field(default=None)
	svgs: str | None = Field(default=None, description="SVGs as text, if exists any")
	updated_at: datetime.datetime | None = Field(default=None)


class BankQuestionsConceptsMapsInsert(CustomModelInsert):
	"""BankQuestionsConceptsMaps Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# bank_question_id: has default value
	# concept_id: has default value
	# created_at: has default value
	
		# Optional fields
	bank_question_id: UUID4 | None = Field(default=None)
	concept_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)


class BoardsInsert(CustomModelInsert):
	"""Boards Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
	# Required fields
	name: str
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class ChaptersInsert(CustomModelInsert):
	"""Chapters Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
	# Required fields
	name: str
	position: str
	subject_id: UUID4
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class ConceptsInsert(CustomModelInsert):
	"""Concepts Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
	# Required fields
	name: str
	page_number: int
	topic_id: UUID4
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class ConceptsActivitiesMapsInsert(CustomModelInsert):
	"""ConceptsActivitiesMaps Insert Schema."""

	# Primary Keys
	

	# Field properties:
	# activity_id: nullable, has default value
	# concept_id: nullable, has default value
	# created_at: has default value
	
		# Optional fields
	activity_id: UUID4 | None = Field(default=None)
	concept_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)


class GenArtifactsInsert(CustomModelInsert):
	"""GenArtifacts Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# updated_at: has default value
	
	# Required fields
	activity_id: UUID4
	name: str
	source_url: str
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class GenImagesInsert(CustomModelInsert):
	"""GenImages Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# file_path: nullable
	# gen_question_id: nullable, has default value
	# img_url: nullable
	# position: nullable
	# svg_string: nullable
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	file_path: str | None = Field(default=None)
	gen_question_id: UUID4 | None = Field(default=None)
	img_url: str | None = Field(default=None)
	position: int | None = Field(default=None)
	svg_string: str | None = Field(default=None)


class GenQuestionVersionsInsert(CustomModelInsert):
	"""GenQuestionVersions Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# correct_mcq_option: nullable
	# created_at: has default value
	# explanation: nullable
	# gen_question_id: nullable
	# is_active: has default value
	# is_deleted: has default value
	# match_the_following_columns: nullable
	# msq_option1_answer: nullable
	# msq_option2_answer: nullable
	# msq_option3_answer: nullable
	# msq_option4_answer: nullable
	# option1: nullable
	# option2: nullable
	# option3: nullable
	# option4: nullable
	# question_text: nullable
	# version_index: has default value
	
	# Required fields
	answer_text: str
	hardness_level: PublicHardnessLevelEnumEnum
	marks: int
	question_type: PublicQuestionTypeEnumEnum
	
		# Optional fields
	correct_mcq_option: int | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	explanation: str | None = Field(default=None)
	gen_question_id: UUID4 | None = Field(default=None)
	is_active: bool | None = Field(default=None)
	is_deleted: bool | None = Field(default=None)
	match_the_following_columns: dict | list[dict] | list[Any] | Json | None = Field(default=None)
	msq_option1_answer: bool | None = Field(default=None)
	msq_option2_answer: bool | None = Field(default=None)
	msq_option3_answer: bool | None = Field(default=None)
	msq_option4_answer: bool | None = Field(default=None)
	option1: str | None = Field(default=None)
	option2: str | None = Field(default=None)
	option3: str | None = Field(default=None)
	option4: str | None = Field(default=None)
	question_text: str | None = Field(default=None)
	version_index: int | None = Field(default=None)


class GenQuestionsInsert(CustomModelInsert):
	"""GenQuestions Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# correct_mcq_option: nullable
	# created_at: has default value
	# explanation: nullable
	# is_exercise_question: has default value
	# is_in_draft: has default value
	# is_new: has default value
	# is_page_break_below: has default value
	# is_solved_example: has default value
	# match_the_following_columns: nullable
	# msq_option1_answer: nullable
	# msq_option2_answer: nullable
	# msq_option3_answer: nullable
	# msq_option4_answer: nullable
	# option1: nullable
	# option2: nullable
	# option3: nullable
	# option4: nullable
	# position_in_draft: nullable
	# qgen_draft_section_id: nullable
	# question_text: nullable
	# updated_at: has default value
	
	# Required fields
	activity_id: UUID4
	answer_text: str = Field(description="Answer for the Generated question. Not For MCQs and MSQs")
	hardness_level: PublicHardnessLevelEnumEnum
	marks: int
	question_type: PublicQuestionTypeEnumEnum
	
		# Optional fields
	correct_mcq_option: int | None = Field(default=None, description="can be 1 or 2 or 3 or 4")
	created_at: datetime.datetime | None = Field(default=None)
	explanation: str | None = Field(default=None, description="explanation for the question and answer")
	is_exercise_question: bool | None = Field(default=None, description="1 if the question is pushed here from the bank question table where is_exercise_question  was true")
	is_in_draft: bool | None = Field(default=None)
	is_new: bool | None = Field(default=None)
	is_page_break_below: bool | None = Field(default=None, description="If the question is in a draft, then this variable will tell if to add a page break after this question in the pdf being generated")
	is_solved_example: bool | None = Field(default=None, description="1 if the question is pushed here from the bank question table where is_solved_example was true")
	match_the_following_columns: dict | list[dict] | list[Any] | Json | None = Field(default=None)
	msq_option1_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	msq_option2_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	msq_option3_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	msq_option4_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	option1: str | None = Field(default=None, description="For MCQ or MSQs")
	option2: str | None = Field(default=None, description="For MCQs or MSQs")
	option3: str | None = Field(default=None, description="For MCQs or MSQs")
	option4: str | None = Field(default=None, description="For MCQs or MSQs")
	position_in_draft: int | None = Field(default=None, description="Position of the question in the section in the draft, if this question belongs to a draft")
	qgen_draft_section_id: UUID4 | None = Field(default=None, description="The id of the section to which this question belongs to if, this is in draft")
	question_text: str | None = Field(default=None, description="Actual Question")
	updated_at: datetime.datetime | None = Field(default=None)


class GenQuestionsConceptsMapsInsert(CustomModelInsert):
	"""GenQuestionsConceptsMaps Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	
	# Required fields
	concept_id: UUID4
	gen_question_id: UUID4
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)


class GenerationPaneConceptsMapsInsert(CustomModelInsert):
	"""GenerationPaneConceptsMaps Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	
	# Required fields
	concept_id: UUID4
	qgen_generation_pane_id: UUID4
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)


class OrgsInsert(CustomModelInsert):
	"""Orgs Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# address: nullable
	# board_id: nullable
	# created_at: has default value
	# header_line: nullable
	# logo_url: nullable
	# org_type: nullable
	# updated_at: has default value
	
	# Required fields
	email: str
	phone_num: str
	
		# Optional fields
	address: str | None = Field(default=None)
	board_id: UUID4 | None = Field(default=None, description="To which board the organisation belongs to")
	created_at: datetime.datetime | None = Field(default=None)
	header_line: str | None = Field(default=None)
	logo_url: str | None = Field(default=None)
	org_type: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class PhonenumOtpsInsert(CustomModelInsert):
	"""PhonenumOtps Insert Schema."""

	# Primary Keys
	phone_number: str

	# Field properties:
	# created_at: has default value
	
	# Required fields
	otp: str
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)


class QgenDraftInstructionsDraftsMapsInsert(CustomModelInsert):
	"""QgenDraftInstructionsDraftsMaps Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# instruction_text: nullable
	# updated_at: nullable, has default value
	
	# Required fields
	qgen_draft_id: UUID4
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	instruction_text: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class QgenDraftSectionsInsert(CustomModelInsert):
	"""QgenDraftSections Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# position_in_draft: has default value
	# qgen_draft_id: nullable, has default value
	# section_name: nullable
	# updated_at: nullable, has default value
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	position_in_draft: int | None = Field(default=None, description="The position of the section in the draft of the paper to be generated as PDF")
	qgen_draft_id: UUID4 | None = Field(default=None)
	section_name: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class QgenDraftsInsert(CustomModelInsert):
	"""QgenDrafts Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# institute_name: nullable
	# logo_url: nullable
	# max_position: nullable, has default value
	# maximum_marks: nullable
	# paper_datetime: nullable
	# paper_duration: nullable
	# paper_subtitle: nullable
	# paper_title: nullable
	# school_class_name: nullable
	# subject_name: nullable
	# updated_at: has default value
	
	# Required fields
	activity_id: UUID4
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	institute_name: str | None = Field(default=None, description="Institute / School Name to be shown on the top of the generated pdf of the paper")
	logo_url: str | None = Field(default=None, description="URL of the logo to be shown on the generated question paper pdf")
	max_position: int | None = Field(default=None)
	maximum_marks: int | None = Field(default=None, description="Maximum / Total Marks to be shown on the generated paper PDF")
	paper_datetime: datetime.datetime | None = Field(default=None, description="The Date and time of examination to be shown on the generated PDF")
	paper_duration: datetime.time | None = Field(default=None, description="Duration of the paper to be shown on the generated PDF")
	paper_subtitle: str | None = Field(default=None, description="Subtitle of the paper to be shown in the generated pdf")
	paper_title: str | None = Field(default=None, description="Title of the Paper to be shown in the generated PDF")
	school_class_name: str | None = Field(default=None)
	subject_name: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class QgenGenerationPanesInsert(CustomModelInsert):
	"""QgenGenerationPanes Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# activity_id: nullable, has default value
	# created_at: has default value
	# custom_instructions: nullable
	# difficulty_level_easy_count: nullable, has default value
	# difficulty_level_hard_count: nullable, has default value
	# difficulty_level_medium_count: nullable, has default value
	# exercise_questions_count: nullable
	# fill_in_the_blanks_count: nullable
	# long_answer_count: nullable
	# match_the_following_count: nullable
	# mcq_count: nullable
	# msq_count: nullable
	# school_class_id: nullable
	# short_answer_count: nullable
	# solved_examples_count: nullable
	# subject_id: nullable
	# total_marks_count: nullable, has default value
	# total_time_count: nullable, has default value
	# true_false_count: nullable
	# updated_at: nullable
	
		# Optional fields
	activity_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	custom_instructions: str | None = Field(default=None)
	difficulty_level_easy_count: int | None = Field(default=None)
	difficulty_level_hard_count: int | None = Field(default=None)
	difficulty_level_medium_count: int | None = Field(default=None)
	exercise_questions_count: int | None = Field(default=None)
	fill_in_the_blanks_count: int | None = Field(default=None)
	long_answer_count: int | None = Field(default=None)
	match_the_following_count: int | None = Field(default=None)
	mcq_count: int | None = Field(default=None)
	msq_count: int | None = Field(default=None)
	school_class_id: UUID4 | None = Field(default=None)
	short_answer_count: int | None = Field(default=None)
	solved_examples_count: int | None = Field(default=None)
	subject_id: UUID4 | None = Field(default=None)
	total_marks_count: int | None = Field(default=None)
	total_time_count: int | None = Field(default=None)
	true_false_count: int | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class SchoolClassesInsert(CustomModelInsert):
	"""SchoolClasses Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
	# Required fields
	board_id: UUID4
	name: str
	position: int
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class SubjectsInsert(CustomModelInsert):
	"""Subjects Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
	# Required fields
	name: str
	school_class_id: UUID4
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class TopicsInsert(CustomModelInsert):
	"""Topics Insert Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)  # has default value

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
	# Required fields
	chapter_id: UUID4
	name: str
	position: str
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class UsersInsert(CustomModelInsert):
	"""Users Insert Schema."""

	# Primary Keys
	id: UUID4

	# Field properties:
	# account_status: has default value
	# avatar_url: nullable
	# created_at: has default value
	# credits: has default value
	# email: nullable
	# is_test_user: has default value
	# last_active_at: has default value
	# name: nullable
	# org_id: nullable
	# phone_num: nullable
	# updated_at: has default value
	# user_entered_school_address: nullable
	# user_entered_school_board: nullable
	# user_entered_school_name: nullable
	
	# Required fields
	user_type: str
	
		# Optional fields
	account_status: str | None = Field(default=None, description="Is account active or disabled or inactive or deactivated etc.")
	avatar_url: str | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	credits: int | None = Field(default=None)
	email: str | None = Field(default=None)
	is_test_user: bool | None = Field(default=None)
	last_active_at: datetime.datetime | None = Field(default=None, description="To track user Churn")
	name: Annotated[str, StringConstraints(**{'max_length': 50})] | None = Field(default=None, description="The Full Name of The User")
	org_id: UUID4 | None = Field(default=None)
	phone_num: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)
	user_entered_school_address: str | None = Field(default=None, description="The School Address which user manually enters, for thus who are not associated with any organisation")
	user_entered_school_board: str | None = Field(default=None, description="The Board which user enters manually, for thus users who are not part of any organisation, and doing a signup via website directly.")
	user_entered_school_name: str | None = Field(default=None, description="The School Name which the User have Entered, for direct login users, not associated with organisation initially")
# UPDATE CLASSES
# Note: These models are used for update operations. All fields are optional.


class ActivitiesUpdate(CustomModelUpdate):
	"""Activities Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# updated_at: has default value
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	name: str | None = Field(default=None)
	product_type: PublicProductTypeEnumEnum | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)
	user_id: UUID4 | None = Field(default=None)


class BankQuestionsUpdate(CustomModelUpdate):
	"""BankQuestions Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# chapter_id: nullable
	# correct_mcq_option: nullable
	# created_at: has default value
	# explanation: nullable
	# figure: nullable
	# hardness_level: nullable, has default value
	# is_from_exercise: has default value
	# is_image_needed: has default value
	# is_incomplete: has default value
	# is_solved_example: has default value
	# is_true: nullable
	# marks: nullable
	# match_columns: nullable
	# msq_option1_answer: nullable
	# msq_option2_answer: nullable
	# msq_option3_answer: nullable
	# msq_option4_answer: nullable
	# option1: nullable
	# option2: nullable
	# option3: nullable
	# option4: nullable
	# reference: nullable
	# svgs: nullable
	# updated_at: nullable, has default value
	
		# Optional fields
	answer_text: str | None = Field(default=None)
	chapter_id: UUID4 | None = Field(default=None)
	correct_mcq_option: int | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	explanation: str | None = Field(default=None)
	figure: str | None = Field(default=None)
	hardness_level: PublicHardnessLevelEnumEnum | None = Field(default=None)
	is_from_exercise: bool | None = Field(default=None, description="1 if from exercise of the textbook, 0 otherwise")
	is_image_needed: bool | None = Field(default=None, description="1 if image is to be inserted yet for the question, 0 otherwise")
	is_incomplete: bool | None = Field(default=None, description="1 if any manual modifications are needed or any errors are there in the question, 0 otherwise")
	is_solved_example: bool | None = Field(default=None, description="1 if it is solved example from the textbook, 0 otherwise")
	is_true: bool | None = Field(default=None, description="This is the answer of the true or false question if present")
	marks: int | None = Field(default=None)
	match_columns: str | None = Field(default=None, description="Columns for the match the following question")
	msq_option1_answer: bool | None = Field(default=None)
	msq_option2_answer: bool | None = Field(default=None)
	msq_option3_answer: bool | None = Field(default=None)
	msq_option4_answer: bool | None = Field(default=None)
	option1: str | None = Field(default=None)
	option2: str | None = Field(default=None)
	option3: str | None = Field(default=None)
	option4: str | None = Field(default=None)
	question_text: str | None = Field(default=None)
	question_type: PublicQuestionTypeEnumEnum | None = Field(default=None)
	reference: str | None = Field(default=None)
	subject_id: UUID4 | None = Field(default=None)
	svgs: str | None = Field(default=None, description="SVGs as text, if exists any")
	updated_at: datetime.datetime | None = Field(default=None)


class BankQuestionsConceptsMapsUpdate(CustomModelUpdate):
	"""BankQuestionsConceptsMaps Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# bank_question_id: has default value
	# concept_id: has default value
	# created_at: has default value
	
		# Optional fields
	bank_question_id: UUID4 | None = Field(default=None)
	concept_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)


class BoardsUpdate(CustomModelUpdate):
	"""Boards Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	name: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class ChaptersUpdate(CustomModelUpdate):
	"""Chapters Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	name: str | None = Field(default=None)
	position: str | None = Field(default=None)
	subject_id: UUID4 | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class ConceptsUpdate(CustomModelUpdate):
	"""Concepts Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	name: str | None = Field(default=None)
	page_number: int | None = Field(default=None)
	topic_id: UUID4 | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class ConceptsActivitiesMapsUpdate(CustomModelUpdate):
	"""ConceptsActivitiesMaps Update Schema."""

	# Primary Keys
	

	# Field properties:
	# activity_id: nullable, has default value
	# concept_id: nullable, has default value
	# created_at: has default value
	
		# Optional fields
	activity_id: UUID4 | None = Field(default=None)
	concept_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)


class GenArtifactsUpdate(CustomModelUpdate):
	"""GenArtifacts Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# updated_at: has default value
	
		# Optional fields
	activity_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	name: str | None = Field(default=None)
	source_url: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class GenImagesUpdate(CustomModelUpdate):
	"""GenImages Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# file_path: nullable
	# gen_question_id: nullable, has default value
	# img_url: nullable
	# position: nullable
	# svg_string: nullable
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	file_path: str | None = Field(default=None)
	gen_question_id: UUID4 | None = Field(default=None)
	img_url: str | None = Field(default=None)
	position: int | None = Field(default=None)
	svg_string: str | None = Field(default=None)


class GenQuestionVersionsUpdate(CustomModelUpdate):
	"""GenQuestionVersions Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# correct_mcq_option: nullable
	# created_at: has default value
	# explanation: nullable
	# gen_question_id: nullable
	# is_active: has default value
	# is_deleted: has default value
	# match_the_following_columns: nullable
	# msq_option1_answer: nullable
	# msq_option2_answer: nullable
	# msq_option3_answer: nullable
	# msq_option4_answer: nullable
	# option1: nullable
	# option2: nullable
	# option3: nullable
	# option4: nullable
	# question_text: nullable
	# version_index: has default value
	
		# Optional fields
	answer_text: str | None = Field(default=None)
	correct_mcq_option: int | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	explanation: str | None = Field(default=None)
	gen_question_id: UUID4 | None = Field(default=None)
	hardness_level: PublicHardnessLevelEnumEnum | None = Field(default=None)
	is_active: bool | None = Field(default=None)
	is_deleted: bool | None = Field(default=None)
	marks: int | None = Field(default=None)
	match_the_following_columns: dict | list[dict] | list[Any] | Json | None = Field(default=None)
	msq_option1_answer: bool | None = Field(default=None)
	msq_option2_answer: bool | None = Field(default=None)
	msq_option3_answer: bool | None = Field(default=None)
	msq_option4_answer: bool | None = Field(default=None)
	option1: str | None = Field(default=None)
	option2: str | None = Field(default=None)
	option3: str | None = Field(default=None)
	option4: str | None = Field(default=None)
	question_text: str | None = Field(default=None)
	question_type: PublicQuestionTypeEnumEnum | None = Field(default=None)
	version_index: int | None = Field(default=None)


class GenQuestionsUpdate(CustomModelUpdate):
	"""GenQuestions Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# correct_mcq_option: nullable
	# created_at: has default value
	# explanation: nullable
	# is_exercise_question: has default value
	# is_in_draft: has default value
	# is_new: has default value
	# is_page_break_below: has default value
	# is_solved_example: has default value
	# match_the_following_columns: nullable
	# msq_option1_answer: nullable
	# msq_option2_answer: nullable
	# msq_option3_answer: nullable
	# msq_option4_answer: nullable
	# option1: nullable
	# option2: nullable
	# option3: nullable
	# option4: nullable
	# position_in_draft: nullable
	# qgen_draft_section_id: nullable
	# question_text: nullable
	# updated_at: has default value
	
		# Optional fields
	activity_id: UUID4 | None = Field(default=None)
	answer_text: str | None = Field(default=None, description="Answer for the Generated question. Not For MCQs and MSQs")
	correct_mcq_option: int | None = Field(default=None, description="can be 1 or 2 or 3 or 4")
	created_at: datetime.datetime | None = Field(default=None)
	explanation: str | None = Field(default=None, description="explanation for the question and answer")
	hardness_level: PublicHardnessLevelEnumEnum | None = Field(default=None)
	is_exercise_question: bool | None = Field(default=None, description="1 if the question is pushed here from the bank question table where is_exercise_question  was true")
	is_in_draft: bool | None = Field(default=None)
	is_new: bool | None = Field(default=None)
	is_page_break_below: bool | None = Field(default=None, description="If the question is in a draft, then this variable will tell if to add a page break after this question in the pdf being generated")
	is_solved_example: bool | None = Field(default=None, description="1 if the question is pushed here from the bank question table where is_solved_example was true")
	marks: int | None = Field(default=None)
	match_the_following_columns: dict | list[dict] | list[Any] | Json | None = Field(default=None)
	msq_option1_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	msq_option2_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	msq_option3_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	msq_option4_answer: bool | None = Field(default=None, description="Describes if the option is correct or incorrect")
	option1: str | None = Field(default=None, description="For MCQ or MSQs")
	option2: str | None = Field(default=None, description="For MCQs or MSQs")
	option3: str | None = Field(default=None, description="For MCQs or MSQs")
	option4: str | None = Field(default=None, description="For MCQs or MSQs")
	position_in_draft: int | None = Field(default=None, description="Position of the question in the section in the draft, if this question belongs to a draft")
	qgen_draft_section_id: UUID4 | None = Field(default=None, description="The id of the section to which this question belongs to if, this is in draft")
	question_text: str | None = Field(default=None, description="Actual Question")
	question_type: PublicQuestionTypeEnumEnum | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class GenQuestionsConceptsMapsUpdate(CustomModelUpdate):
	"""GenQuestionsConceptsMaps Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	
		# Optional fields
	concept_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	gen_question_id: UUID4 | None = Field(default=None)


class GenerationPaneConceptsMapsUpdate(CustomModelUpdate):
	"""GenerationPaneConceptsMaps Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	
		# Optional fields
	concept_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	qgen_generation_pane_id: UUID4 | None = Field(default=None)


class OrgsUpdate(CustomModelUpdate):
	"""Orgs Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# address: nullable
	# board_id: nullable
	# created_at: has default value
	# header_line: nullable
	# logo_url: nullable
	# org_type: nullable
	# updated_at: has default value
	
		# Optional fields
	address: str | None = Field(default=None)
	board_id: UUID4 | None = Field(default=None, description="To which board the organisation belongs to")
	created_at: datetime.datetime | None = Field(default=None)
	email: str | None = Field(default=None)
	header_line: str | None = Field(default=None)
	logo_url: str | None = Field(default=None)
	org_type: str | None = Field(default=None)
	phone_num: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class PhonenumOtpsUpdate(CustomModelUpdate):
	"""PhonenumOtps Update Schema."""

	# Primary Keys
	phone_number: str | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	otp: str | None = Field(default=None)


class QgenDraftInstructionsDraftsMapsUpdate(CustomModelUpdate):
	"""QgenDraftInstructionsDraftsMaps Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# instruction_text: nullable
	# updated_at: nullable, has default value
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	instruction_text: str | None = Field(default=None)
	qgen_draft_id: UUID4 | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class QgenDraftSectionsUpdate(CustomModelUpdate):
	"""QgenDraftSections Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# position_in_draft: has default value
	# qgen_draft_id: nullable, has default value
	# section_name: nullable
	# updated_at: nullable, has default value
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	position_in_draft: int | None = Field(default=None, description="The position of the section in the draft of the paper to be generated as PDF")
	qgen_draft_id: UUID4 | None = Field(default=None)
	section_name: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class QgenDraftsUpdate(CustomModelUpdate):
	"""QgenDrafts Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# institute_name: nullable
	# logo_url: nullable
	# max_position: nullable, has default value
	# maximum_marks: nullable
	# paper_datetime: nullable
	# paper_duration: nullable
	# paper_subtitle: nullable
	# paper_title: nullable
	# school_class_name: nullable
	# subject_name: nullable
	# updated_at: has default value
	
		# Optional fields
	activity_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	institute_name: str | None = Field(default=None, description="Institute / School Name to be shown on the top of the generated pdf of the paper")
	logo_url: str | None = Field(default=None, description="URL of the logo to be shown on the generated question paper pdf")
	max_position: int | None = Field(default=None)
	maximum_marks: int | None = Field(default=None, description="Maximum / Total Marks to be shown on the generated paper PDF")
	paper_datetime: datetime.datetime | None = Field(default=None, description="The Date and time of examination to be shown on the generated PDF")
	paper_duration: datetime.time | None = Field(default=None, description="Duration of the paper to be shown on the generated PDF")
	paper_subtitle: str | None = Field(default=None, description="Subtitle of the paper to be shown in the generated pdf")
	paper_title: str | None = Field(default=None, description="Title of the Paper to be shown in the generated PDF")
	school_class_name: str | None = Field(default=None)
	subject_name: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class QgenGenerationPanesUpdate(CustomModelUpdate):
	"""QgenGenerationPanes Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# activity_id: nullable, has default value
	# created_at: has default value
	# custom_instructions: nullable
	# difficulty_level_easy_count: nullable, has default value
	# difficulty_level_hard_count: nullable, has default value
	# difficulty_level_medium_count: nullable, has default value
	# exercise_questions_count: nullable
	# fill_in_the_blanks_count: nullable
	# long_answer_count: nullable
	# match_the_following_count: nullable
	# mcq_count: nullable
	# msq_count: nullable
	# school_class_id: nullable
	# short_answer_count: nullable
	# solved_examples_count: nullable
	# subject_id: nullable
	# total_marks_count: nullable, has default value
	# total_time_count: nullable, has default value
	# true_false_count: nullable
	# updated_at: nullable
	
		# Optional fields
	activity_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	custom_instructions: str | None = Field(default=None)
	difficulty_level_easy_count: int | None = Field(default=None)
	difficulty_level_hard_count: int | None = Field(default=None)
	difficulty_level_medium_count: int | None = Field(default=None)
	exercise_questions_count: int | None = Field(default=None)
	fill_in_the_blanks_count: int | None = Field(default=None)
	long_answer_count: int | None = Field(default=None)
	match_the_following_count: int | None = Field(default=None)
	mcq_count: int | None = Field(default=None)
	msq_count: int | None = Field(default=None)
	school_class_id: UUID4 | None = Field(default=None)
	short_answer_count: int | None = Field(default=None)
	solved_examples_count: int | None = Field(default=None)
	subject_id: UUID4 | None = Field(default=None)
	total_marks_count: int | None = Field(default=None)
	total_time_count: int | None = Field(default=None)
	true_false_count: int | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class SchoolClassesUpdate(CustomModelUpdate):
	"""SchoolClasses Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
		# Optional fields
	board_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	name: str | None = Field(default=None)
	position: int | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class SubjectsUpdate(CustomModelUpdate):
	"""Subjects Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
		# Optional fields
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	name: str | None = Field(default=None)
	school_class_id: UUID4 | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class TopicsUpdate(CustomModelUpdate):
	"""Topics Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# created_at: has default value
	# description: nullable
	# updated_at: has default value
	
		# Optional fields
	chapter_id: UUID4 | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	description: str | None = Field(default=None)
	name: str | None = Field(default=None)
	position: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)


class UsersUpdate(CustomModelUpdate):
	"""Users Update Schema."""

	# Primary Keys
	id: UUID4 | None = Field(default=None)

	# Field properties:
	# account_status: has default value
	# avatar_url: nullable
	# created_at: has default value
	# credits: has default value
	# email: nullable
	# is_test_user: has default value
	# last_active_at: has default value
	# name: nullable
	# org_id: nullable
	# phone_num: nullable
	# updated_at: has default value
	# user_entered_school_address: nullable
	# user_entered_school_board: nullable
	# user_entered_school_name: nullable
	
		# Optional fields
	account_status: str | None = Field(default=None, description="Is account active or disabled or inactive or deactivated etc.")
	avatar_url: str | None = Field(default=None)
	created_at: datetime.datetime | None = Field(default=None)
	credits: int | None = Field(default=None)
	email: str | None = Field(default=None)
	is_test_user: bool | None = Field(default=None)
	last_active_at: datetime.datetime | None = Field(default=None, description="To track user Churn")
	name: Annotated[str, StringConstraints(**{'max_length': 50})] | None = Field(default=None, description="The Full Name of The User")
	org_id: UUID4 | None = Field(default=None)
	phone_num: str | None = Field(default=None)
	updated_at: datetime.datetime | None = Field(default=None)
	user_entered_school_address: str | None = Field(default=None, description="The School Address which user manually enters, for thus who are not associated with any organisation")
	user_entered_school_board: str | None = Field(default=None, description="The Board which user enters manually, for thus users who are not part of any organisation, and doing a signup via website directly.")
	user_entered_school_name: str | None = Field(default=None, description="The School Name which the User have Entered, for direct login users, not associated with organisation initially")
	user_type: str | None = Field(default=None)


# OPERATIONAL CLASSES


class Activities(ActivitiesBaseSchema):
	"""Activities Schema for Pydantic.

	Inherits from ActivitiesBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	user: Users | None = Field(default=None)
	concepts_activities_map: ConceptsActivitiesMaps | None = Field(default=None)
	gen_artifacts: list[GenArtifacts] | None = Field(default=None)
	gen_questions: list[GenQuestions] | None = Field(default=None)
	qgen_draft: QgenDrafts | None = Field(default=None)
	qgen_generation_pane: QgenGenerationPanes | None = Field(default=None)


class BankQuestions(BankQuestionsBaseSchema):
	"""BankQuestions Schema for Pydantic.

	Inherits from BankQuestionsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	chapter: Chapters | None = Field(default=None)
	subject: Subjects | None = Field(default=None)
	bank_questions_concepts_maps: list[BankQuestionsConceptsMaps] | None = Field(default=None)


class BankQuestionsConceptsMaps(BankQuestionsConceptsMapsBaseSchema):
	"""BankQuestionsConceptsMaps Schema for Pydantic.

	Inherits from BankQuestionsConceptsMapsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	bank_question: BankQuestions | None = Field(default=None)
	concept: Concepts | None = Field(default=None)


class Boards(BoardsBaseSchema):
	"""Boards Schema for Pydantic.

	Inherits from BoardsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	orgs: list[Orgs] | None = Field(default=None)
	school_class: SchoolClasses | None = Field(default=None)


class Chapters(ChaptersBaseSchema):
	"""Chapters Schema for Pydantic.

	Inherits from ChaptersBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	subject: Subjects | None = Field(default=None)
	bank_questions: list[BankQuestions] | None = Field(default=None)
	topic: Topics | None = Field(default=None)


class Concepts(ConceptsBaseSchema):
	"""Concepts Schema for Pydantic.

	Inherits from ConceptsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	topic: Topics | None = Field(default=None)
	bank_questions_concepts_maps: list[BankQuestionsConceptsMaps] | None = Field(default=None)
	concepts_activities_map: ConceptsActivitiesMaps | None = Field(default=None)
	gen_questions_concepts_map: GenQuestionsConceptsMaps | None = Field(default=None)
	generation_pane_concepts_maps: list[GenerationPaneConceptsMaps] | None = Field(default=None)


class ConceptsActivitiesMaps(ConceptsActivitiesMapsBaseSchema):
	"""ConceptsActivitiesMaps Schema for Pydantic.

	Inherits from ConceptsActivitiesMapsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	activity: Activities | None = Field(default=None)
	concept: Concepts | None = Field(default=None)


class GenArtifacts(GenArtifactsBaseSchema):
	"""GenArtifacts Schema for Pydantic.

	Inherits from GenArtifactsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	activity: Activities | None = Field(default=None)


class GenImages(GenImagesBaseSchema):
	"""GenImages Schema for Pydantic.

	Inherits from GenImagesBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	gen_question: GenQuestions | None = Field(default=None)


class GenQuestionVersions(GenQuestionVersionsBaseSchema):
	"""GenQuestionVersions Schema for Pydantic.

	Inherits from GenQuestionVersionsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	gen_question: GenQuestions | None = Field(default=None)


class GenQuestions(GenQuestionsBaseSchema):
	"""GenQuestions Schema for Pydantic.

	Inherits from GenQuestionsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	activity: Activities | None = Field(default=None)
	qgen_draft_section: QgenDraftSections | None = Field(default=None)
	gen_images: list[GenImages] | None = Field(default=None)
	gen_question_versions: list[GenQuestionVersions] | None = Field(default=None)
	gen_questions_concepts_map: GenQuestionsConceptsMaps | None = Field(default=None)


class GenQuestionsConceptsMaps(GenQuestionsConceptsMapsBaseSchema):
	"""GenQuestionsConceptsMaps Schema for Pydantic.

	Inherits from GenQuestionsConceptsMapsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	gen_question: GenQuestions | None = Field(default=None)
	concept: Concepts | None = Field(default=None)


class GenerationPaneConceptsMaps(GenerationPaneConceptsMapsBaseSchema):
	"""GenerationPaneConceptsMaps Schema for Pydantic.

	Inherits from GenerationPaneConceptsMapsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	concept: Concepts | None = Field(default=None)
	qgen_generation_pane: QgenGenerationPanes | None = Field(default=None)


class Orgs(OrgsBaseSchema):
	"""Orgs Schema for Pydantic.

	Inherits from OrgsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	board: Boards | None = Field(default=None)
	users: list[Users] | None = Field(default=None)


class PhonenumOtps(PhonenumOtpsBaseSchema):
	"""PhonenumOtps Schema for Pydantic.

	Inherits from PhonenumOtpsBaseSchema. Add any customization here.
	"""
	pass


class QgenDraftInstructionsDraftsMaps(QgenDraftInstructionsDraftsMapsBaseSchema):
	"""QgenDraftInstructionsDraftsMaps Schema for Pydantic.

	Inherits from QgenDraftInstructionsDraftsMapsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	qgen_draft: QgenDrafts | None = Field(default=None)


class QgenDraftSections(QgenDraftSectionsBaseSchema):
	"""QgenDraftSections Schema for Pydantic.

	Inherits from QgenDraftSectionsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	qgen_draft: QgenDrafts | None = Field(default=None)
	gen_questions: list[GenQuestions] | None = Field(default=None)


class QgenDrafts(QgenDraftsBaseSchema):
	"""QgenDrafts Schema for Pydantic.

	Inherits from QgenDraftsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	activity: Activities | None = Field(default=None)
	qgen_draft_instructions_drafts_maps: list[QgenDraftInstructionsDraftsMaps] | None = Field(default=None)
	qgen_draft_sections: list[QgenDraftSections] | None = Field(default=None)


class QgenGenerationPanes(QgenGenerationPanesBaseSchema):
	"""QgenGenerationPanes Schema for Pydantic.

	Inherits from QgenGenerationPanesBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	activity: Activities | None = Field(default=None)
	school_class: SchoolClasses | None = Field(default=None)
	subject: Subjects | None = Field(default=None)
	generation_pane_concepts_maps: list[GenerationPaneConceptsMaps] | None = Field(default=None)


class SchoolClasses(SchoolClassesBaseSchema):
	"""SchoolClasses Schema for Pydantic.

	Inherits from SchoolClassesBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	board: Boards | None = Field(default=None)
	qgen_generation_panes: list[QgenGenerationPanes] | None = Field(default=None)
	subject: Subjects | None = Field(default=None)


class Subjects(SubjectsBaseSchema):
	"""Subjects Schema for Pydantic.

	Inherits from SubjectsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	school_class: SchoolClasses | None = Field(default=None)
	bank_questions: list[BankQuestions] | None = Field(default=None)
	chapter: Chapters | None = Field(default=None)
	qgen_generation_panes: list[QgenGenerationPanes] | None = Field(default=None)


class Topics(TopicsBaseSchema):
	"""Topics Schema for Pydantic.

	Inherits from TopicsBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	chapter: Chapters | None = Field(default=None)
	concept: Concepts | None = Field(default=None)


class Users(UsersBaseSchema):
	"""Users Schema for Pydantic.

	Inherits from UsersBaseSchema. Add any customization here.
	"""

	# Foreign Keys
	org: Orgs | None = Field(default=None)
	activities: Activities | None = Field(default=None)
