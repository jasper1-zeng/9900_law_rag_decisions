# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
import json
import os
from fuzzywuzzy import process
from openai import OpenAI
import os

class SatscraperPipeline:
    def process_case_title(self, text):
        pattern = r"\[?\d{4}\]?\s*WASAT\s*\d+\s*\(\d+\s\w+\s+\d{4}\)"
        new_text = re.sub(r"[\t\n'\"\[\]]", " ", text) # remove special characters
        return re.sub(pattern, "", new_text).strip()
    
    def replace_char(self, text):
        if not isinstance(text, str):
            return text  # Return non-string values as-is
        new_text = re.sub(r"[\t\n'\"\[\]]", " ", text) # remove special characters
        # https://stackoverflow.com/questions/1546226/is-there-a-simple-way-to-remove-multiple-spaces-in-a-string
        return re.sub(' +', ' ', new_text)
    
    def process_reasons(self, text):
        new_text = re.sub(r"[\t\n'\"\[\]]", " ", text) # remove special characters
        return re.sub(' +', ' ', new_text)
    
    def process_citation_number(self, text):
        new_text = re.sub(r"[\t\n]", " ", text)
        return re.sub(r"[\[\]]", "", new_text)
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        field_names = adapter.field_names()

        for field_name in field_names:
            value = adapter.get(field_name)
            if field_name == 'case_url' or field_name == 'case_topic':
                continue         
            elif field_name == 'citation_number':
                adapter[field_name] = self.process_citation_number(value)
            elif field_name == 'case_title':
                adapter[field_name] = self.process_case_title(value)
            elif field_name == 'case_year':
                if adapter[field_name] != 'N/A':
                    adapter[field_name] = int(adapter[field_name])   
            elif field_name == 'reasons':
                adapter[field_name] = self.process_reasons(value)
            else:
                adapter[field_name] = self.replace_char(value)

            # elif field_name == 'citation_number':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'case_act':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'member':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'heard_date':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'delivery_date':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'file_no':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'case_between':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'catchwords':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'legislations':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'result':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'category':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'representation':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'referred_cases':
            #     adapter[field_name] = self.replace_char(value)
            # elif field_name == 'reasons':
            #     adapter[field_name] = self.replace_char(value)

        return item

class TopicMappingPipeline:
    def __init__(self):
        # Load the topic_act_mapping.json file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        mapping_path = os.path.join(current_dir, 'topic_act_mapping.json')
        with open(mapping_path, 'r') as f:
            self.mapping_data = json.load(f)
        
        # Create a flattened dictionary where key=act, value=topic for faster lookups
        self.act_to_topic = {}
        for case_topic, acts in self.mapping_data['topic_act_mapping'].items():
            for act in acts:
                self.act_to_topic[act] = case_topic
        
        # Create a list of all acts for fuzzy matching
        self.all_acts = list(self.act_to_topic.keys())
    
    def find_topic_for_act(self, case_act):
        # If case_act is empty or None, return "Other"
        if not case_act or case_act == 'N/A':
            return "Other"
        
        try:
            # Try fuzzy matching to find the closest act in our mapping
            match, score = process.extractOne(case_act, self.all_acts)
            
            # Only use the match if the score is high enough
            if score >= 75: # 75 is the threshold for fuzzy matching (can be adjusted)
                return self.act_to_topic[match]
            else:
                # You can adjust what to return for no close matches
                return "Other"
        except Exception as e:
            print(f"Error during fuzzy matching: {str(e)}")
            return "Other"
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        case_act = adapter.get('case_act')
        
        # Add a new field 'case_topic' based on the case_act
        adapter['case_topic'] = self.find_topic_for_act(case_act)
        
        return item
    
# https://thepythonscrapyplaybook.com/scrapy-beginners-guide-storing-data/
# pip install psycopg2
# pip install sentence-transformers           (this is to generate the embeddings)
# must have pgvector installed (instructions located https://github.com/pgvector/pgvector)
import psycopg2
from datetime import datetime
from sentence_transformers import SentenceTransformer

class SavingToPostgresPipeline(object):
    def __init__(self):
        # Initialise huggingface model
        # https://huggingface.co/intfloat/e5-base-v2
        self.model = SentenceTransformer('intfloat/e5-base-v2')

        self.conn = psycopg2.connect(
            host="localhost",
            database="satdata",
            user="postgres",
            password="ilagan123")
        
        self.curr = self.conn.cursor()
        
        # Enable pgvector
        self.curr.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # Define expected columns and their types
        expected_schema = [
            ("id", "SERIAL PRIMARY KEY"),
            ("case_url", "TEXT UNIQUE"),
            ("case_title", "TEXT"),
            ("citation_number", "TEXT"),
            ("case_year", "TEXT"),
            ("case_act", "TEXT"),
            ("case_topic", "TEXT"),
            ("member", "TEXT"),
            ("heard_date", "DATE"),
            ("delivery_date", "DATE"),         
            ("file_no", "TEXT"),
            ("case_between", "TEXT"),   
            ("catchwords", "TEXT"),
            ("legislations", "TEXT"),
            ("result", "TEXT"),
            ("category", "TEXT"),
            ("representation", "TEXT"),               
            ("referred_cases", "TEXT"),
            ("reasons", "TEXT"),
            ("reasons_summary", "TEXT"),
            ("reasons_summary_embedding", "vector(768)")
        ]
        
        # Check if the table exists
        self.curr.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'satdata')")
        table_exists = self.curr.fetchone()[0]
        
        # If table exists, check if schema matches expected schema
        if table_exists:
            # Get current schema
            self.curr.execute("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'satdata'
                ORDER BY ordinal_position
            """)
            
            current_schema = self.curr.fetchall()
            schema_mismatch = False
            
            print("Checking schema compatibility...")
            
            # Check if column count matches
            if len(current_schema) != len(expected_schema):
                print(f"Schema mismatch: Current schema has {len(current_schema)} columns, expected {len(expected_schema)}")
                schema_mismatch = True
            
            # Drop table if schema doesn't match
            if schema_mismatch:
                print("Schema mismatch detected. Dropping and recreating the table...")
                self.curr.execute("DROP TABLE IF EXISTS satdata CASCADE")
                self.conn.commit()
                table_exists = False
                
        # Create table if it doesn't exist
        if not table_exists:
            print("Creating satdata table with the latest schema...")
            self.curr.execute("""
            CREATE TABLE IF NOT EXISTS satdata(
                id SERIAL PRIMARY KEY,
                case_url TEXT UNIQUE,
                case_title TEXT,
                citation_number TEXT,
                case_year TEXT,
                case_act TEXT,
                case_topic TEXT,
                member TEXT,
                heard_date DATE,
                delivery_date DATE,         
                file_no TEXT,
                case_between TEXT,   
                catchwords TEXT,
                legislations TEXT,
                result TEXT,
                category TEXT,
                representation TEXT,               
                referred_cases TEXT,
                reasons TEXT,
                reasons_summary TEXT,
                reasons_summary_embedding vector(768)
            )
            """)
            
            # Create an index on topic for faster searching
            self.curr.execute("""
            CREATE INDEX IF NOT EXISTS case_topic_idx ON satdata (case_topic)
            """)
            
            self.conn.commit()
            print("Table created successfully.")
        else:
            print("Using existing satdata table (schema is compatible).")

        # Create the reasons_chunks table if it doesn't exist
        self.curr.execute("""
            CREATE TABLE IF NOT EXISTS reasons_chunks (
                id SERIAL PRIMARY KEY,
                case_id INTEGER REFERENCES satdata(id) ON DELETE CASCADE,
                case_topic TEXT,
                chunk_index INTEGER,
                chunk_text TEXT,
                chunk_embedding vector(768)
            )
        """)
        self.conn.commit()

    def process_item(self, item, spider):
        # Convert date text into date format
        # https://www.datacamp.com/tutorial/converting-strings-datetime-objects
        # https://www.digitalocean.com/community/tutorials/python-string-to-datetime-strptime
        def convert_date_text(date_text):
            try:
                return datetime.strptime(date_text, "%d %B %Y").date()
            except:
                return None
        
        # Generate text embedding using huggingface model 
        # https://huggingface.co/intfloat/e5-base-v2
        def generate_embedding_from_chunks(chunks):
            return self.model.encode(chunks, normalize_embeddings=True).tolist() # generate embedding (convert from numpy array -> list)
        
        def generate_embedding_from_text(text):
            return self.model.encode(text, normalize_embeddings=True).tolist() # generate embedding (convert from numpy array -> list)

        # Function to chunk text
        # pip install langchain
        # https://www.pinecone.io/learn/chunking-strategies/
        # https://python.langchain.com/v0.1/docs/modules/data_connection/document_transformers/recursive_text_splitter/
        def generate_chunks(text):
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=5000, 
                chunk_overlap=500, 
                separators=[
                    "\n\n",
                    "\n",
                    ". ",
                    " ",
                    ""
                ])
            chunks = text_splitter.split_text(text)
            chunks = [f"passage: {chunk}" for chunk in chunks] # this is required for e5-base-v2 model
            return chunks
        
        # Function to generate summary from text
        # https://medium.com/@Doug-Creates/nightmares-and-client-chat-completions-create-29ad0acbe16a
        # https://docs.vllm.ai/en/latest/getting_started/examples/openai_chat_completion_client.html
        def generate_summary(text):
            api_key = os.getenv("OPENAI_API_KEY")
            client = OpenAI(api_key=api_key)  # Create a client instance
            
            prompt = f"""
            Please summarise the following State Administrative Tribunal (SAT) decision cases following the below format:

            1. Introduction - A brief overview of the case and what it concerns.
            2. Background - Context about the parties involved and the nature of the dispute.
            3. Relevant Acts and Legislation - Highlight the referenced acts and legislation.
            4. Key Arguments - Outline the main arguments presented by involved parties.
            5. Key Insights - Summarise the reasons for the tribunal and the key findings.
            6. Outcome - Which parties won and lost the case. Detail why the respective parties won/lost.
            
            Reasons for the tribunal:
            {text}
            """
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are assisting judges and lawyers in summarising legal decisions for their reference."},
                    {"role": "user", "content": f"{prompt}" }
                ],
                temperature=0.3,
                max_tokens=2048
            )

            summary = response.choices[0].message.content
            return summary
            
        ## First, check if a record with this case_url already exists
        self.curr.execute("SELECT id FROM satdata WHERE case_url = %s", (item['case_url'],))
        existing_record = self.curr.fetchone()
        
        # Define variables which will be used to store generated fields
        generated_heard_date = convert_date_text(item['heard_date'])
        generated_delivery_date = convert_date_text(item['delivery_date'])
        
        # Handle reasons (chunks and embedding)
        generated_reasons_chunks = generate_chunks(item['reasons'])
        generated_reasons_embedding = generate_embedding_from_chunks(generated_reasons_chunks)

        # Handle reasons_summary
        testing = False # variable to speed up testing without having to wait for generating summaries
        if not testing:
            generated_reasons_summary = generate_summary(item['reasons'])
            generated_reasons_summary_embedding = generate_embedding_from_text(generated_reasons_summary)
        else:
            generated_reasons_summary = 'N/A'
            generated_reasons_summary_embedding = generate_embedding_from_text(generated_reasons_summary)
        
        if existing_record:
            # Update existing record
            self.curr.execute("""
            UPDATE satdata SET
                case_title = %s,
                citation_number = %s,
                case_year = %s,
                case_act = %s,
                case_topic = %s,
                member = %s,
                heard_date = %s,
                delivery_date = %s,
                file_no = %s,
                case_between = %s,
                catchwords = %s,
                legislations = %s,
                result = %s,
                category = %s,
                representation = %s,
                referred_cases = %s,
                reasons = %s,
                reasons_summary = %s,
                reasons_summary_embedding = %s
            WHERE case_url = %s
            """, (
                item['case_title'],
                item['citation_number'],
                item['case_year'],
                item['case_act'],
                item['case_topic'],
                item['member'],
                generated_heard_date,
                generated_delivery_date,
                item['file_no'],
                item['case_between'],
                item['catchwords'],
                item['legislations'],
                item['result'],
                item['category'],
                item['representation'],
                item['referred_cases'],
                item['reasons'],
                generated_reasons_summary,
                generated_reasons_summary_embedding,
                item['case_url']
            ))
            case_id = existing_record[0]
        else:
            # Insert new record
            self.curr.execute(""" insert into satdata (
                case_url,
                case_title, 
                citation_number, 
                case_year,
                case_act, 
                case_topic,
                member, 
                heard_date,
                delivery_date,
                file_no,
                case_between,
                catchwords,
                legislations,
                result,
                category,
                representation,
                referred_cases,
                reasons,
                reasons_summary,
                reasons_summary_embedding
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (
                item['case_url'],
                item['case_title'],
                item['citation_number'],
                item['case_year'],
                item['case_act'],
                item['case_topic'],
                item['member'],
                generated_heard_date,
                generated_delivery_date,
                item['file_no'],
                item['case_between'],
                item['catchwords'],
                item['legislations'],
                item['result'],
                item['category'],
                item['representation'],
                item['referred_cases'],
                item['reasons'],
                generated_reasons_summary,
                generated_reasons_summary_embedding
            ))
            self.conn.commit()
            self.curr.execute("SELECT id FROM satdata WHERE case_url = %s", (item['case_url'],))
            case_id = self.curr.fetchone()[0]
        
        # Store reasons_chunks in new table
        self.curr.execute("DELETE FROM reasons_chunks WHERE case_id = %s", (case_id,))
        for i in range(len(generated_reasons_chunks)):
            self.curr.execute("""
                INSERT INTO reasons_chunks (case_id, case_topic, chunk_index, chunk_text, chunk_embedding)
                VALUES (%s, %s, %s, %s, %s)
            """, (case_id, item['case_topic'], i, generated_reasons_chunks[i], generated_reasons_embedding[i]))

        ## Execute insert of data into database
        self.conn.commit()
        return item

    def close_spider(self, spider):
        ## Close cursor & connection to database 
        self.curr.close()
        self.conn.close()