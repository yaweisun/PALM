# coding=utf-8
import paddlepalm as palm
import json
from paddlepalm.distribute import gpu_dev_count

if __name__ == '__main__':
 
    # configs
    max_seqlen = 256
    batch_size = 16
    num_epochs = 6
    lr = 5e-5
    num_classes = 7
    weight_decay = 0.01
    dropout_prob = 0.1
    vocab_path = './pretrain/ernie-zh-base/vocab.txt'
    label_map = './data/label_map.json'
    random_seed = 1
    train_file = './data/train.tsv'
    predict_file = './data/test.tsv'
    
    save_path='./outputs/'
    save_type='ckpt' 
    pre_params = './pretrain/ernie-zh-base/params'
    config = json.load(open('./pretrain/ernie-zh-base/ernie_config.json'))
    input_dim = config['hidden_size']  
    task_name = 'msra_ner'
    pred_output = './outputs/predict/'
    train_print_steps = 10
    pred_print_steps = 20
    
    # -----------------------  for training ----------------------- 

    # step 1-1: create readers for training
    ner_reader = palm.reader.SequenceLabelReader(vocab_path, max_seqlen, label_map, seed=random_seed)
    # step 1-2: load the training data
    ner_reader.load_data(train_file, file_format='tsv', num_epochs=num_epochs, batch_size=batch_size)
    
    # step 2: create a backbone of the model to extract text features
    ernie = palm.backbone.ERNIE.from_config(config)

    # step 3: register the backbone in reader
    ner_reader.register_with(ernie)

    # step 4: create the task output head
    ner_head = palm.head.SequenceLabel(num_classes, input_dim, dropout_prob)

    # step 5-1: create a task trainer
    trainer = palm.Trainer(task_name)
    # step 5-2: build forward graph with backbone and task head
    loss_var = trainer.build_forward(ernie, ner_head)

    # step 6-1*: use warmup
    n_steps = ner_reader.num_examples * num_epochs // batch_size
    warmup_steps = int(0.1 * n_steps)
    print('total_steps: {}'.format(n_steps))
    print('warmup_steps: {}'.format(warmup_steps))
    sched = palm.lr_sched.TriangularSchedualer(warmup_steps, n_steps)
    # step 6-2: create a optimizer
    adam = palm.optimizer.Adam(loss_var, lr, sched)
    # step 6-3: build backward
    trainer.build_backward(optimizer=adam, weight_decay=weight_decay)
  
    # step 7: fit prepared reader and data
    trainer.fit_reader(ner_reader)

    # step 8-1*: load pretrained parameters
    trainer.load_pretrain(pre_params)
    # step 8-2*: set saver to save model
    save_steps = (n_steps-20)
    print('save_steps: {}'.format(save_steps))
    trainer.set_saver(save_path=save_path, save_steps=save_steps, save_type=save_type)
    # step 8-3: start training
    trainer.train(print_steps=train_print_steps)
   
    # -----------------------  for prediction ----------------------- 

    # step 1-1: create readers for prediction
    print('prepare to predict...')
    predict_ner_reader = palm.reader.SequenceLabelReader(vocab_path, max_seqlen, label_map, phase='predict')
    # step 1-2: load the training data
    predict_ner_reader.load_data(predict_file, batch_size)
   
    # step 2: create a backbone of the model to extract text features
    pred_ernie = palm.backbone.ERNIE.from_config(config, phase='predict')
    
    # step 3: register the backbone in reader
    predict_ner_reader.register_with(pred_ernie)

    # step 4: create the task output head
    ner_pred_head = palm.head.SequenceLabel(num_classes, input_dim, phase='predict')
    
    # step 5: build forward graph with backbone and task head
    trainer.build_predict_forward(pred_ernie, ner_pred_head)
    
    # step 6: load pretrained model
    pred_model_path = './outputs/ckpt.step' + str(save_steps)
    pred_ckpt = trainer.load_ckpt(pred_model_path)
    
    # step 7: fit prepared reader and data
    trainer.fit_reader(predict_ner_reader, phase='predict')
   
    # step 8: predict
    print('predicting..')
    trainer.predict(print_steps=pred_print_steps, output_dir=pred_output)
