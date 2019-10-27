import argparse
import logging
import os
import sys

from sklearn.metrics import precision_recall_fscore_support, confusion_matrix

from algorithms.dataset_factory import DatasetFactory
from trainpipelinesbuilders.BertTrainInferenceBuilder import BertTrainInferenceBuilder


def run(dataset_factory_name, network_factory_name, train_file, val_file, model_dir, out_dir,
        epochs,
        earlystoppingpatience, additionalargs):
    logger = logging.getLogger(__name__)

    dataset_factory = DatasetFactory().get_datasetfactory(dataset_factory_name)

    train, val = dataset_factory.get_dataset(train_file), dataset_factory.get_dataset(val_file)

    if not os.path.exists(out_dir) or not os.path.isdir(out_dir):
        raise FileNotFoundError("The path {} should exist and must be a directory".format(out_dir))

    if not os.path.exists(model_dir) or not os.path.isdir(model_dir):
        raise FileNotFoundError("The path {} should exist and must be a directory".format(model_dir))

    builder = BertTrainInferenceBuilder(dataset=train,
                                        model_dir=model_dir, output_dir=out_dir, epochs=epochs,
                                        patience_epochs=earlystoppingpatience,
                                        extra_args=additionalargs, network_factory_name=network_factory_name)
    train_pipeline = builder.get_trainpipeline()
    val_results, val_actuals, val_predicted = train_pipeline(train, val)
    precision, recall, fscore, support = precision_recall_fscore_support(val_actuals, val_predicted,
                                                                         average='binary',
                                                                         pos_label=train.positive_label)
    tn, fp, fn, tp = confusion_matrix(val_actuals, val_predicted).ravel()

    logger.info("Confusion matrix: tn, fp, fn, tp  is {}".format((tn, fp, fn, tp)))
    logger.info("Scores: precision, recall, fscore, support {}".format((precision, recall, fscore, support)))
    logger.info(" F-score is {}".format(fscore))

    return val_results, val_actuals, val_predicted


if "__main__" == __name__:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", help="The dataset type", choices=DatasetFactory().dataset_factory_names,
                        required=True)

    parser.add_argument("--network", help="The network type", choices={"RelationExtractorBioBertFactory"},
                        default="RelationExtractorBioBertFactory")

    parser.add_argument("--trainfile",
                        help="The input train file wrt to train  dir", required=True)

    parser.add_argument("--traindir",
                        help="The input train  dir", default=os.environ.get("SM_CHANNEL_TRAIN", "."))

    parser.add_argument("--valfile",
                        help="The input val file wrt to val  dir", required=True)

    parser.add_argument("--valdir",
                        help="The input val dir", default=os.environ.get("SM_CHANNEL_VAL", "."))

    parser.add_argument("--pretrained_biobert_dir", help="The pretained biobert model dir",
                        default=os.environ.get("SM_CHANNEL_PRETRAINED_BIOBERT", None))

    parser.add_argument("--outdir", help="The output dir", default=os.environ.get("SM_OUTPUT_DATA_DIR", "."))

    parser.add_argument("--modeldir", help="The output dir", default=os.environ.get("SM_MODEL_DIR", "."))

    parser.add_argument("--epochs", help="The number of epochs", type=int, default=10)

    parser.add_argument("--earlystoppingpatience", help="The number of pateince epochs epochs", type=int, default=10)

    parser.add_argument("--interaction-type", help="The interction type", default=None)

    parser.add_argument("--log-level", help="Log level", default="INFO", choices={"INFO", "WARN", "DEBUG", "ERROR"})

    args, additional = parser.parse_known_args()

    # Convert additional args into dict
    print(additional)
    additional_dict = {}
    for i in range(0, len(additional), 2):
        additional_dict[additional[i].lstrip("--")] = additional[i + 1]

    print(args.__dict__)
    print(additional_dict)
    # Set up logging
    logging.basicConfig(level=logging.getLevelName(args.log_level), handlers=[logging.StreamHandler(sys.stdout)],
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    additional_dict["pretrained_biobert_dir"] = args.pretrained_biobert_dir

    trainjson = os.path.join(args.traindir, args.trainfile)
    valjson = os.path.join(args.valdir, args.valfile)
    run(args.dataset, args.network, trainjson, valjson,
        args.modeldir, args.outdir, args.epochs, args.earlystoppingpatience, additional_dict)
