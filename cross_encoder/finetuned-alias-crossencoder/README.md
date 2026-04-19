---
tags:
- sentence-transformers
- cross-encoder
- reranker
- generated_from_trainer
- dataset_size:2006
- loss:BinaryCrossEntropyLoss
base_model: cross-encoder/ms-marco-MiniLM-L6-v2
pipeline_tag: text-ranking
library_name: sentence-transformers
metrics:
- accuracy
- accuracy_threshold
- f1
- f1_threshold
- precision
- recall
- average_precision
model-index:
- name: CrossEncoder based on cross-encoder/ms-marco-MiniLM-L6-v2
  results:
  - task:
      type: cross-encoder-binary-classification
      name: Cross Encoder Binary Classification
    dataset:
      name: test
      type: test
    metrics:
    - type: accuracy
      value: 0.9900398406374502
      name: Accuracy
    - type: accuracy_threshold
      value: -5.298148155212402
      name: Accuracy Threshold
    - type: f1
      value: 0.9905123339658444
      name: F1
    - type: f1_threshold
      value: -5.298148155212402
      name: F1 Threshold
    - type: precision
      value: 1.0
      name: Precision
    - type: recall
      value: 0.981203007518797
      name: Recall
    - type: average_precision
      value: 0.9976832949939449
      name: Average Precision
---

# CrossEncoder based on cross-encoder/ms-marco-MiniLM-L6-v2

This is a [Cross Encoder](https://www.sbert.net/docs/cross_encoder/usage/usage.html) model finetuned from [cross-encoder/ms-marco-MiniLM-L6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) using the [sentence-transformers](https://www.SBERT.net) library. It computes scores for pairs of texts, which can be used for text reranking and semantic search.

## Model Details

### Model Description
- **Model Type:** Cross Encoder
- **Base model:** [cross-encoder/ms-marco-MiniLM-L6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) <!-- at revision c5ee24cb16019beea0893ab7796b1df96625c6b8 -->
- **Maximum Sequence Length:** 512 tokens
- **Number of Output Labels:** 1 label
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Documentation:** [Cross Encoder Documentation](https://www.sbert.net/docs/cross_encoder/usage/usage.html)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Cross Encoders on Hugging Face](https://huggingface.co/models?library=sentence-transformers&other=cross-encoder)

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import CrossEncoder

# Download from the 🤗 Hub
model = CrossEncoder("cross_encoder_model_id")
# Get scores for pairs of texts
pairs = [
    ['Сергей Васильевич Рахманинов', 'Fleetwood Mac'],
    ['Пётр Ильич Чайковский', 'Ilyitch'],
    ['Robert Schumann', 'Robert Shumann'],
    ['Ella Fitzgerald', 'John Lennon'],
    ['コナミ矩形波倶楽部', 'こなみ くけいは くらぶ'],
]
scores = model.predict(pairs)
print(scores.shape)
# (5,)

# Or rank different texts based on similarity to a single text
ranks = model.rank(
    'Сергей Васильевич Рахманинов',
    [
        'Fleetwood Mac',
        'Ilyitch',
        'Robert Shumann',
        'John Lennon',
        'こなみ くけいは くらぶ',
    ]
)
# [{'corpus_id': ..., 'score': ...}, {'corpus_id': ..., 'score': ...}, ...]
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### Metrics

#### Cross Encoder Binary Classification

* Dataset: `test`
* Evaluated with [<code>CEBinaryClassificationEvaluator</code>](https://sbert.net/docs/package_reference/cross_encoder/evaluation.html#sentence_transformers.cross_encoder.evaluation.CEBinaryClassificationEvaluator)

| Metric                | Value      |
|:----------------------|:-----------|
| accuracy              | 0.99       |
| accuracy_threshold    | -5.2981    |
| f1                    | 0.9905     |
| f1_threshold          | -5.2981    |
| precision             | 1.0        |
| recall                | 0.9812     |
| **average_precision** | **0.9977** |

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 2,006 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence_0                                                                                    | sentence_1                                                                                    | label                                                          |
  |:--------|:----------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------|:---------------------------------------------------------------|
  | type    | string                                                                                        | string                                                                                        | float                                                          |
  | details | <ul><li>min: 2 characters</li><li>mean: 14.95 characters</li><li>max: 29 characters</li></ul> | <ul><li>min: 2 characters</li><li>mean: 13.91 characters</li><li>max: 54 characters</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.48</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence_0                                | sentence_1                  | label            |
  |:------------------------------------------|:----------------------------|:-----------------|
  | <code>Сергей Васильевич Рахманинов</code> | <code>Fleetwood Mac</code>  | <code>0.0</code> |
  | <code>Пётр Ильич Чайковский</code>        | <code>Ilyitch</code>        | <code>1.0</code> |
  | <code>Robert Schumann</code>              | <code>Robert Shumann</code> | <code>1.0</code> |
* Loss: [<code>BinaryCrossEntropyLoss</code>](https://sbert.net/docs/package_reference/cross_encoder/losses.html#binarycrossentropyloss) with these parameters:
  ```json
  {
      "activation_fn": "torch.nn.modules.linear.Identity",
      "pos_weight": null
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 16
- `num_train_epochs`: 50
- `eval_strategy`: steps
- `per_device_eval_batch_size`: 16

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `per_device_train_batch_size`: 16
- `num_train_epochs`: 50
- `max_steps`: -1
- `learning_rate`: 5e-05
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_steps`: 0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `optim_target_modules`: None
- `gradient_accumulation_steps`: 1
- `average_tokens_across_devices`: True
- `max_grad_norm`: 1
- `label_smoothing_factor`: 0.0
- `bf16`: False
- `fp16`: False
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `use_cache`: False
- `neftune_noise_alpha`: None
- `torch_empty_cache_steps`: None
- `auto_find_batch_size`: False
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `include_num_input_tokens_seen`: no
- `log_level`: passive
- `log_level_replica`: warning
- `disable_tqdm`: False
- `project`: huggingface
- `trackio_space_id`: trackio
- `eval_strategy`: steps
- `per_device_eval_batch_size`: 16
- `prediction_loss_only`: True
- `eval_on_start`: False
- `eval_do_concat_batches`: True
- `eval_use_gather_object`: False
- `eval_accumulation_steps`: None
- `include_for_metrics`: []
- `batch_eval_metrics`: False
- `save_only_model`: False
- `save_on_each_node`: False
- `enable_jit_checkpoint`: False
- `push_to_hub`: False
- `hub_private_repo`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_always_push`: False
- `hub_revision`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `restore_callback_states_from_checkpoint`: False
- `full_determinism`: False
- `seed`: 42
- `data_seed`: None
- `use_cpu`: False
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `dataloader_prefetch_factor`: None
- `remove_unused_columns`: True
- `label_names`: None
- `train_sampling_strategy`: random
- `length_column_name`: length
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `ddp_backend`: None
- `ddp_timeout`: 1800
- `fsdp`: []
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `deepspeed`: None
- `debug`: []
- `skip_memory_metrics`: True
- `do_predict`: False
- `resume_from_checkpoint`: None
- `warmup_ratio`: None
- `local_rank`: -1
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: proportional
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch   | Step | Training Loss | test_average_precision |
|:-------:|:----:|:-------------:|:----------------------:|
| 1.0     | 126  | -             | 0.9330                 |
| 1.5873  | 200  | -             | 0.9382                 |
| 2.0     | 252  | -             | 0.9402                 |
| 3.0     | 378  | -             | 0.9470                 |
| 3.1746  | 400  | -             | 0.9476                 |
| 3.9683  | 500  | 1.8218        | -                      |
| 4.0     | 504  | -             | 0.9532                 |
| 4.7619  | 600  | -             | 0.9591                 |
| 5.0     | 630  | -             | 0.9615                 |
| 6.0     | 756  | -             | 0.9672                 |
| 6.3492  | 800  | -             | 0.9695                 |
| 7.0     | 882  | -             | 0.9725                 |
| 7.9365  | 1000 | 0.3285        | 0.9772                 |
| 8.0     | 1008 | -             | 0.9773                 |
| 9.0     | 1134 | -             | 0.9803                 |
| 9.5238  | 1200 | -             | 0.9834                 |
| 10.0    | 1260 | -             | 0.9847                 |
| 11.0    | 1386 | -             | 0.9874                 |
| 11.1111 | 1400 | -             | 0.9876                 |
| 11.9048 | 1500 | 0.2026        | -                      |
| 12.0    | 1512 | -             | 0.9895                 |
| 12.6984 | 1600 | -             | 0.9913                 |
| 13.0    | 1638 | -             | 0.9912                 |
| 14.0    | 1764 | -             | 0.9931                 |
| 14.2857 | 1800 | -             | 0.9936                 |
| 15.0    | 1890 | -             | 0.9938                 |
| 15.8730 | 2000 | 0.1247        | 0.9951                 |
| 16.0    | 2016 | -             | 0.9954                 |
| 17.0    | 2142 | -             | 0.9957                 |
| 17.4603 | 2200 | -             | 0.9964                 |
| 18.0    | 2268 | -             | 0.9959                 |
| 19.0    | 2394 | -             | 0.9966                 |
| 19.0476 | 2400 | -             | 0.9967                 |
| 19.8413 | 2500 | 0.0721        | -                      |
| 20.0    | 2520 | -             | 0.9974                 |
| 20.6349 | 2600 | -             | 0.9975                 |
| 21.0    | 2646 | -             | 0.9971                 |
| 22.0    | 2772 | -             | 0.9976                 |
| 22.2222 | 2800 | -             | 0.9977                 |


### Framework Versions
- Python: 3.14.1
- Sentence Transformers: 5.3.0
- Transformers: 5.3.0
- PyTorch: 2.10.0
- Accelerate: 1.13.0
- Datasets: 4.8.3
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->