import pandas as pd
from datasets import load_dataset
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

# grab the resume dataset from huggingface
try:
    dataset = load_dataset("AzharAli05/resume-screening-dataset")
    df = dataset['train'].to_pandas()
except Exception as e:
    print(f"dataset load failed: {e}")
    exit()

print(f"got {len(df)} records from dataset")

# only use the good matches for training
try:
    positive_pairs = df[df['Decision'] == 'select']
except KeyError:
    print("can't find 'Decision' column")
    print("available columns:", df.columns.tolist())
    exit()

if positive_pairs.empty:
    print("no 'select' decisions found")
    print("decision values:", df['Decision'].unique())
    exit()

# build training examples from job-resume pairs
train_examples = []
for index, row in positive_pairs.iterrows():
    job_desc = row['Job_Description']
    resume_text = row['Resume']
    train_examples.append(InputExample(texts=[job_desc, resume_text]))

print(f"made {len(train_examples)} training examples")

# pick a base model to start with
model_name = 'all-MiniLM-L6-v2'
print(f"loading {model_name}...")
model = SentenceTransformer(model_name)

# batch size of 16 works well for most gpus
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)

# use multiple negatives ranking loss - good for this kind of task
train_loss = losses.MultipleNegativesRankingLoss(model)

# train for 1 epoch, should be enough to see improvement
num_epochs = 1
warmup_steps = int(len(train_dataloader) * num_epochs * 0.1)

print("\nstarting training...")
model.fit(train_objectives=[(train_dataloader, train_loss)],
          epochs=num_epochs,
          warmup_steps=warmup_steps,
          output_path='./finetuned_model',
          show_progress_bar=True)

print("\ndone! model saved to './finetuned_model'")