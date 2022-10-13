import os
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import Response, JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional, List
import motor.motor_asyncio

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
db = client.germans


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class VocabModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    german: str = Field(...)
    english: str = Field(...)
    korean: str = Field(...)
    audio_url: str = Field(...)
    image_url: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "german": "Kaffee",
                "english": "coffee",
                "korean": "커피",
                "audio_url": "https://audio.dict.cc/speak.audio.v2.php?error_as_text=1&type=mp3&id=67073&lang=de_rec_ip&lp=DEEN",
                "image_url": "https://images.unsplash.com/photo-1571478287153-a888447264e7?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2148&q=80"
            }
        }


class UpdateVocabModel(BaseModel):
    german: Optional[str]
    english: Optional[str]
    korean: Optional[str]
    audio_url: Optional[str]
    image_url: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "german": "Kaffee",
                "english": "coffee",
                "korean": "커피"
            }
        }


@app.post("/", response_description="Add a new word", response_model=VocabModel)
async def create_vocab(vocab: VocabModel = Body(...)):
    vocab = jsonable_encoder(vocab)
    new_vocab = await db["vocabs"].insert_one(vocab)
    created_vocab = await db["vocabs"].find_one({"_id": new_vocab.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_vocab)


@app.get(
    "/", response_description="List all words", response_model=List[VocabModel]
)
async def list_vocabs():
    vocabs = await db["vocabs"].find().to_list(100)
    return vocabs


@app.get(
    "/{id}", response_description="Get a word", response_model=VocabModel
)
async def show_vocab(id: str):
    if (vocab := await db["vocabs"].find_one({"_id": id})) is not None:
        return vocab

    raise HTTPException(status_code=404, detail=f"Vocab {id} not found")


@app.put("/{id}", response_description="Update a word", response_model=VocabModel)
async def update_vocab(id: str, vocab: UpdateVocabModel = Body(...)):
    vocab = {k: v for k, v in vocab.dict().items() if v is not None}

    if len(vocab) >= 1:
        update_result = await db["vocabs"].update_one({"_id": id}, {"$set": vocab})

        if update_result.modified_count == 1:
            if (
                updated_vocab := await db["vocabs"].find_one({"_id": id})
            ) is not None:
                return updated_vocab

    if (existing_vocab := await db["vocabs"].find_one({"_id": id})) is not None:
        return existing_vocab

    raise HTTPException(status_code=404, detail=f"Vocab {id} not found")


@app.delete("/{id}", response_description="Delete a vocab")
async def delete_vocab(id: str):
    delete_result = await db["vocabs"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Vocab {id} not found")
