[![Build Status](https://travis-ci.org/elangovana/kegg-pathway-extractor.svg?branch=master)](https://travis-ci.org/elangovana/kegg-pathway-extractor)

# PPI typed relation extraction
Protein - protein interactions (PPI) play a very important role in various aspects of cell biology (Zhou & He, 2008). The PPI interactions form complex networks and can be represented as a graph, where each node represents a protein and an edge represents a type of relationship between the 2 proteins.
Manually curating these networks by reading journals and regularly maintaining them with the latest information is beyond human lifespan (Baumgartner, Cohen, Fox, Acquaah-Mensah, & Hunter, 2007). 

### Task definition
For instance, in the sentence “Full-length cPLA2 was phosphorylated stoichiometrically by p42 mitogen-activated protein (MAP) kinase  in vitro” , 
-	The protein name recognition phase recognizes “cPLA2” & “p42 mitogen-activated protein (MAP) kinase” as protein names. Some entity recognition tasks also involve recognizing the entity roles, such as “cPLA2” as the theme or the target protein, and “p42 mitogen-activated protein (MAP) kinase” as the agent protein or the source of the interaction.
-	The protein-protein interaction extraction task recognizes “phosphorylate” as the relationship between “cPLA2” & “p42 mitogen-activated protein (MAP) kinase”.


# Prerequisite
1. Data
   Get the MIPS Interaction XML file & extract
   ```shell
   wget http://mips.helmholtz-muenchen.de/proj/ppi/data/mppi.gz
   gunzip mppi.gz 
   ```  
2. Download pretrained word embeddings
https://drive.google.com/file/d/0B7XkCwpI5KDYNlNUTTlSS21pQmM/edit?usp=sharing

## Run Docker

### Download and analyse the dataset with elastic search
#### Visualise
1. Sample download intact files with pattern human0* and elastic search index
    ```bash
    region=$1
    esdomain=$2
    accesskey=$3
    accesssecret=$4
    s3path=$5
 
    basedata=/home/ubuntu/data
    file_pattern=human0*
 
    script=scripts/run_pipeline_download_esindex.sh
    sudo docker run -v ${basedata}:/data --env elasticsearch_domain_name=$esdomain --env AWS_ACCESS_KEY_ID=$accesskey   --env AWS_REGION=$region --env AWS_SECRET_ACCESS_KEY=$accesssecret lanax/kegg-pathway-extractor:latest $script /data $file_pattern $s3path 
    ```

#### Prepare dataset


1. Download dataset from Imex ftp site ftp.ebi.ac.uk
    ```bash
    basedata=/home/ubuntu/data
 
    sudo docker run -v ${basedata}:/data  scripts/dowloadintactinteractions.sh /data  "<filepattern e.g. human*.xml>" "<optional s3 destination>"
    ```


## Run locally from source

### Training and Validation

1. Download dataset from Imex ftp site ftp.ebi.ac.uk
    ```bash
    cd ./source
    bash scripts/dowloadintactinteractions.sh "<localdir>" "<filepattern e.g. human*.xml>" "<optional s3 destination>"
    ```

2. Create raw but json formatted dataset locally from source
    
    ```bash
    export PYTHONPATH=./source
    python source/pipeline/main_pipeline_dataprep.py "<inputdir containing imex xml files>" "outputdir"
    ```
3. Create pubtator formatted abstracts so that GnormPlus can recognises entities

    ```bash
    export PYTHONPATH=./source
    python source/dataformatters/main_formatter.py "<datafilecreatedfrompreviousstep>" "<outputfile>"
    ```
4.  Extract entities using GNormPlus
    
    ```bash
    docker pull lanax/gnormplus
    cp 
    docker run -it -v /data/:/gnormdata lanax/gnormplus

    # within docker
    # Step1  edit the setup.txt to human specifies only..
    # Step 2 run process
    java -Xmx10G -Xms10G -jar /GNormPlusJava/GNormPlus.jar /gnormdata/input /gnormdata/output setup.txt > /gnormdata/gnormplus.log 2>&1 &

    ```
    
    Sample setup.txt
    
    ```text
    
    #===Annotation
    #Attribution setting:
    #FocusSpecies = Taxonomy ID
    #	All: All species
    #	9606: Human
    #	4932: yeast
    #	7227: Fly
    #	10090: Mouse
    #	10116: Rat
    #	7955: Zebrafish
    #	3702: Arabidopsis thaliana
    #open: True
    #close: False
    
    [Focus Species]
        FocusSpecies = 9606
    [Dictionary & Model]
        DictionaryFolder = Dictionary
        GNRModel = Dictionary/GNR.Model
        SCModel = Dictionary/SimConcept.Model
        GeneIDMatch = True
        Normalization2Protein = False
        DeleteTmp = True


    ```
    
    
4. Download NCBI to Uniprot Id mapping file
   
   From https://www.uniprot.org/downloads , download the ID mapping file ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/. This contains the ID mapping between UNIPROT and NCBI. We need this as GNormplus use NCBI gene id and we need the protein names.
   The dat file contains three columns, delimited by tab:
   
    - UniProtKB-AC 
    - ID_type 
    - ID
    
    e.g 
    ```text
    P43405	DNASU	6850
    P43405	GeneID	6850
    P43405	GenomeRNAi	6850
    A0A024R244	GeneID	6850
    A0A024R244	GenomeRNAi	6850
    A0A024R273	GeneID	6850
    A0A024R273	GenomeRNAi	6850
    A8K4G2	DNASU	6850
    ```
 
4. Download wordtovec pretrained models (either pubmed+pmc trained or  pubmed+pmc+wikipedia)and convert to text format 

    ```bash
    # Download word to vec trained only on pubmed and pmc
    wget  wget -O /data/PubMed-and-PMC-w2v.bin http://evexdb.org/pmresources/vec-space-models/PubMed-and-PMC-w2v.bin
 
    python ./source/dataformatters/main_wordToVecBinToText.py /data/PubMed-and-PMC-w2v.bin /data/PubMed-and-PMC-w2v.bin.txt
    ```
    
    ```bash
    # Download word to vec trained only on pubmed and pmc and wikipedia
    wget  wget -O /data/PubMed-and-PMC-w2v.bin http://evexdb.org/pmresources/vec-space-models/wikipedia-pubmed-and-PMC-w2v.bin
 
    python ./source/dataformatters/main_wordToVecBinToText.py /data/wikipedia-pubmed-and-PMC-w2v.bin /data/wikipedia-pubmed-and-PMC-w2v.bin.txt
    ```

4. Run the data exploration notebook [DataExploration.ipynb](DataExploration.ipynb) to clean data, generate negative samples and  normalise abstract 

4. Run train job
    ```bash
    export PYTHONPATH=./source
    python source/algorithms/main_train.py Linear train.json val.json ./tests/test_algorithms/sample_PubMed-and-PMC-w2v.bin.txt 200 outdir
    ```

5. Consolidated train + predict
    ```bash
     #!/usr/bin/env bash
    
        
     set -e
     set -x
  
     # Init
     # Type of network, Linear is MLP, Cnn is Cnn, CnnPos is with position embedding
     network=CnnPos
     base_dir=/data
     s3_dest=s3://yourbucket/results
    
    
     fmtdt=`date +"%y%m%d_%H%M"`
     base_name=model_${network}_${fmtdt}
     outdir=${base_dir}/${base_name}
     echo ${outdir}
     mkdir ${outdir}
      
     export PYTHONPATH="./source"
     
     mkdir ${outdir}
     
     # Git head to trace to source to reproduce run
     git log -1 > ${outdir}/run.log
     
     # Train
     python ./source/algorithms/main_train.py ${network}  /data/train_unique_pub_v3_lessnegatve.json /data/val_unique_pub_v3_lessnegatve.json /data/wikipedia-pubmed-and-PMC-w2v.bin.txt 200 ${outdir}  --epochs 50  --log-level INFO >> ${outdir}/run.log 2>&1
     
     # Predict on validation set
     python ./source/algorithms/main_predict.py ${network}  /data/test_unique_pub_v3_lessnegatve.json ${outdir}  ${outdir} >> ${outdir}/run.log 2>&1
     mv ${outdir}/predicted.json ${outdir}/predicted_test_unique_pub_v3_lessnegatve.json
     
     # Predict on test set
     python ./source/algorithms/main_predict.py ${network}  /data/val_unique_pub_v3_lessnegatve.json ${outdir}  ${outdir} >> ${outdir}/run.log 2>&1
     mv ${outdir}/predicted.json ${outdir}/predicted_val_unique_pub_v3_lessnegatve.json
    
     #Copy results to s3
     aws s3 sync ${outdir} ${s3_dest}/${base_name} >> ${outdir}/synclog 2>&1
    
    ```
    
### Large scale inference on pubmed abstracts

1. Download pubmed FTP and convert to json. For more details see https://github.com/elangovana/pubmed-downloader/tree/master 

1. Convert json to pubtator format to prepare the dataset for GNormPlus

    ```bash
    export PYTHONPATH=./source
    python source/dataformatters/pubmed_abstracts_to_pubtator_format.py "<inputdir_jsonfiles_result_of_step_1>" "<destination_dir_pubtator_format>"
    ```
1. Run GNormPlus to recognise entities using the pubtator formatted files from the previous step, without protein names  normalisation. See https://github.com/elangovana/docker-gnormplus 

1. Generate json using the results of GNormplus annotations in pubtator format.
    ```bash
    export PYTHONPATH=./source
    python ./source/datatransformer/pubtator_annotations_inference_transformer.py tests/test_datatransformer/data_sample_annotation /tmp tmpmap.dat
    ```

1. Run inference
    ```bash
     python ./algorithms/main_predict.py Cnn /data/val_unique_pub_v6_less_negative.json /tmp/model_artefacts /tmp --positives-filter-threshold .95

    ```
