# Generate Questions API

## Endpoint

```
POST /api/v1/generate/questions
```

## Authentication

**Required**: Bearer token in Authorization header

```
Authorization: Bearer <supabase_access_token>
```

The user must be authenticated via Supabase Auth. Obtain the access token by signing in through Supabase client.

---

## Request

### Headers

| Header          | Type   | Required | Description                      |
| --------------- | ------ | -------- | -------------------------------- |
| `Authorization` | string | Yes      | `Bearer <supabase_access_token>` |
| `Content-Type`  | string | Yes      | `application/json`               |

### Body

```json
{
  "activity_id": "uuid",
  "concept_ids": ["uuid", "uuid", ...],
  "config": {
    "question_types": [
      { "type": "string", "count": number }
    ],
    "difficulty_distribution": {
      "easy": number,
      "medium": number,
      "hard": number
    }
  }
}
```

### Body Parameters

| Field                                   | Type    | Required | Description                                                                                                     |
| --------------------------------------- | ------- | -------- | --------------------------------------------------------------------------------------------------------------- |
| `activity_id`                           | UUID    | Yes      | The ID of the activity to associate generated questions with                                                    |
| `concept_ids`                           | UUID[]  | Yes      | Array of concept IDs to generate questions from                                                                 |
| `config`                                | object  | Yes      | Configuration for question generation                                                                           |
| `config.question_types`                 | array   | Yes      | Array of question type configurations                                                                           |
| `config.question_types[].type`          | string  | Yes      | One of: `mcq4`, `msq4`, `fill_in_the_blank`, `true_false`, `short_answer`, `long_answer`, `match_the_following` |
| `config.question_types[].count`         | integer | Yes      | Number of questions to generate for this type                                                                   |
| `config.difficulty_distribution`        | object  | Yes      | Percentage distribution of difficulty levels                                                                    |
| `config.difficulty_distribution.easy`   | integer | Yes      | Percentage of easy questions (0-100)                                                                            |
| `config.difficulty_distribution.medium` | integer | Yes      | Percentage of medium questions (0-100)                                                                          |
| `config.difficulty_distribution.hard`   | integer | Yes      | Percentage of hard questions (0-100)                                                                            |

### Question Types

| Type                  | Description                                                       |
| --------------------- | ----------------------------------------------------------------- |
| `mcq4`                | Multiple Choice Question with 4 options, 1 correct answer         |
| `msq4`                | Multiple Select Question with 4 options, multiple correct answers |
| `fill_in_the_blank`   | Fill in the blank question                                        |
| `true_false`          | True/False question                                               |
| `short_answer`        | Short answer question                                             |
| `long_answer`         | Long answer/essay question                                        |
| `match_the_following` | Match the following question with two columns                     |

---

## Response

### Success Response

**Status Code**: `201 Created`

**Body**: Empty (no content)

The generated questions are stored in the database:

- Questions are inserted into the `gen_questions` table
- Concept-question mappings are inserted into the `gen_questions_concepts_maps` table

### Error Responses

| Status Code                 | Description                             |
| --------------------------- | --------------------------------------- |
| `401 Unauthorized`          | Missing or invalid authentication token |
| `422 Unprocessable Entity`  | Invalid request body (validation error) |
| `500 Internal Server Error` | Server error during question generation |

#### 401 Unauthorized

```json
{
  "detail": "Missing Authorization token"
}
```

or

```json
{
  "detail": "Invalid or expired token"
}
```

#### 422 Unprocessable Entity

```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "activity_id"],
      "msg": "Input should be a valid string",
      "input": "invalid-uuid"
    }
  ]
}
```

---

## Example Request

### cURL

```bash
curl -X POST "https://your-api-domain.com/api/v1/generate/questions" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "activity_id": "550e8400-e29b-41d4-a716-446655440000",
    "concept_ids": [
      "660e8400-e29b-41d4-a716-446655440001",
      "660e8400-e29b-41d4-a716-446655440002"
    ],
    "config": {
      "question_types": [
        { "type": "mcq4", "count": 5 },
        { "type": "true_false", "count": 3 },
        { "type": "short_answer", "count": 2 }
      ],
      "difficulty_distribution": {
        "easy": 30,
        "medium": 50,
        "hard": 20
      }
    }
  }'
```

### JavaScript/TypeScript (fetch)

```typescript
const response = await fetch("/api/v1/generate/questions", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    activity_id: "550e8400-e29b-41d4-a716-446655440000",
    concept_ids: [
      "660e8400-e29b-41d4-a716-446655440001",
      "660e8400-e29b-41d4-a716-446655440002",
    ],
    config: {
      question_types: [
        { type: "mcq4", count: 5 },
        { type: "true_false", count: 3 },
        { type: "short_answer", count: 2 },
      ],
      difficulty_distribution: {
        easy: 30,
        medium: 50,
        hard: 20,
      },
    },
  }),
});

if (response.status === 201) {
  console.log("Questions generated successfully");
  // Fetch generated questions from gen_questions table
}
```

### JavaScript/TypeScript (Supabase + fetch)

```typescript
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Get current session
const {
  data: { session },
} = await supabase.auth.getSession();

if (!session) {
  throw new Error("User not authenticated");
}

const response = await fetch("/api/v1/generate/questions", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${session.access_token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    activity_id: activityId,
    concept_ids: selectedConceptIds,
    config: {
      question_types: [{ type: "mcq4", count: 5 }],
      difficulty_distribution: {
        easy: 40,
        medium: 40,
        hard: 20,
      },
    },
  }),
});
```

---

## TypeScript Types

```typescript
// Request types
type QuestionType =
  | "mcq4"
  | "msq4"
  | "fill_in_the_blank"
  | "true_false"
  | "short_answer"
  | "long_answer"
  | "match_the_following";

interface QuestionTypeConfig {
  type: QuestionType;
  count: number;
}

interface DifficultyDistribution {
  easy: number; // 0-100
  medium: number; // 0-100
  hard: number; // 0-100
}

interface QuestionConfig {
  question_types: QuestionTypeConfig[];
  difficulty_distribution: DifficultyDistribution;
}

interface GenerateQuestionsRequest {
  activity_id: string; // UUID
  concept_ids: string[]; // Array of UUIDs
  config: QuestionConfig;
}
```

---

## Notes

1. **Processing Time**: This endpoint calls an AI model (Gemini) to generate questions, so response time may be 10-60+ seconds depending on the number of questions requested.

2. **Question Storage**: Generated questions are automatically stored in the database. After a successful `201` response, query the `gen_questions` table filtering by `activity_id` to retrieve the generated questions.

3. **Historical Data**: The API uses existing questions from `bank_questions` table as reference for generating new questions that match the style and format.

4. **Difficulty Distribution**: The percentages in `difficulty_distribution` indicate the target distribution. The actual distribution may vary slightly based on AI generation.

5. **Concept Coverage**: Questions are distributed across the provided concepts based on AI analysis of the concepts and historical question data.

---

## Related Database Tables

| Table                         | Description                                       |
| ----------------------------- | ------------------------------------------------- |
| `gen_questions`               | Stores generated questions                        |
| `gen_questions_concepts_maps` | Maps generated questions to concepts              |
| `concepts`                    | Source concepts for question generation           |
| `activities`                  | Parent activity that owns the generated questions |
| `bank_questions`              | Historical questions used as reference            |
