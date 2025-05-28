# Reference is made here:
# https://www.youtube.com/watch?v=2TJxpyO3ei4&t=840s&ab_channel=pixegami
# https://github.com/pixegami/rag-tutorial-v2/blob/main/populate_database.py

from langchain.document_loaders.pdf import PyPDFDirectoryLoader # pip install pypdf langchain # pip install -U langchain-community
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
import psycopg2

DATA_PATH = "data"

# Load pdf documents
def load_documents():
    document_loader = PyPDFDirectoryLoader(DATA_PATH)
    return document_loader.load()

def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=5000,
        chunk_overlap=500,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)

# Generate text embedding using huggingface model 
# https://huggingface.co/intfloat/e5-base-v2
def generate_embedding_from_text(model, text):
    return model.encode(text, normalize_embeddings=True).tolist() # generate embedding (convert from numpy array -> list)

# Create (or update) the data store.
documents = load_documents() # list of documents
chunks = split_documents(documents) # outputs a list of documents

# Example chunk
# page_content='MONOPOLY 
# Property Trading Game from Parker Brothers" 
# AGES 8+ 
# 2 to 8 Players 
# Contents: Gameboard, 3 dice, tokens, 32 houses, I2 hotels, Chance 
# and Community Chest cards, Title Deed cards, play money and a Banker's tray. 
# Now there's a faster way to play MONOPOLY. Choose to play by 
# the classic rules for buying, renting and selling properties or use the 
# Speed Die to get into the action faster. If you've never played the classic 
# MONOPOLY game, refer to the Classic Rules beginning on the next page. 
# If you already know how to play and want to use the Speed Die, just 
# read the section below for the additional Speed Die rules. 
# SPEED DIE RULES 
# Learnins how to Play with the S~eed Die IS as 
# / 
# fast as playing with i't. 
# 1. When starting the game, hand out an extra $1,000 to each player' metadata={'producer': 'Adobe Acrobat 7.0 Paper Capture Plug-in', 'creator': 'Adobe Acrobat 7.0', 'creationdate': '2007-05-03T12:38:10-04:00', 'moddate': '2007-05-03T12:52:41-04:00', 'source': 'data\\monopoly.pdf', 'total_pages': 8, 'page': 0, 'page_label': '1'}


# print(chunks[0].page_content)
# print(chunks[0].metadata['source'])

from sentence_transformers import SentenceTransformer
# Initialise huggingface model
# https://huggingface.co/intfloat/e5-base-v2
model = SentenceTransformer('intfloat/e5-base-v2')

conn = psycopg2.connect(
    host="localhost",
    database="satdata",
    user="postgres",
    password="ilagan123")

curr = conn.cursor()

# Enable pgvector
curr.execute("CREATE EXTENSION IF NOT EXISTS vector")

# Create the uploaded_docs table if it doesn't exist
curr.execute("""
    CREATE TABLE IF NOT EXISTS uploaded_docs (
        id SERIAL PRIMARY KEY,
        document_id TEXT,
        chunk_index INTEGER,
        chunk_text TEXT,
        chunk_embedding vector(768)
    )
""")

# Process documents
chunk_index = 0
prev_document_id = ''
for chunk in chunks:
    document_id = 'mod:' + chunk.metadata['moddate'] + '/' + 'create:' + chunk.metadata['creationdate'] + '/' + 'source:' + chunk.metadata['source']
    if prev_document_id != document_id:
        chunk_index = 0

    # Check if document already exists in database
    curr.execute("""
        SELECT 1 FROM uploaded_docs
        WHERE document_id = %s AND chunk_index = %s
    """, (document_id, chunk_index))
    if curr.fetchone():
        continue

    chunk_text = f"passage: {chunk.page_content}"
    chunk_embedding = generate_embedding_from_text(model, chunk_text)
    curr.execute("""
        INSERT INTO uploaded_docs (document_id, chunk_index, chunk_text, chunk_embedding)
        VALUES (%s, %s, %s, %s)
    """, (document_id, chunk_index, chunk_text, chunk_embedding))
    chunk_index += 1
    prev_document_id = document_id
conn.commit()

# Move documents to processed folder
# https://pynative.com/python-move-files/#:~:text=Use%20the%20shutil.move()%20function&text=move()%20function%20is%20used,(src%2C%20dst)%20function.
import shutil
import os
import glob

# Define source and destination folders
source_folder = "data/"
destination_folder = "data/processed/"

pattern = "*.pdf"
files = glob.glob(source_folder + pattern)

# Move all files
for file in files:
    file_name = os.path.basename(file)
    shutil.move(file, destination_folder + file_name)
