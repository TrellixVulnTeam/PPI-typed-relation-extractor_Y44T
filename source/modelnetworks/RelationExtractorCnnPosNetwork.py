import logging
import math

import torch
import torch.nn as nn

from algorithms.PositionEmbedder import PositionEmbedder


class RelationExtractorCnnPosNetwork(nn.Module):

    def __init__(self, class_size, embedding_dim, feature_lengths, entity_markers, embed_vocab_size=0,
                 ngram_context_size=5, seed=777,
                 drop_rate=.1, pos_embedder=None, dropout_rate_cnn=.5, dropout_rate_fc=0.5, cnn_output=50,
                 fc_layer_size=100, fine_tune_embeddings=True):
        self.fine_tune_embeddings = fine_tune_embeddings
        self.entity_markers = entity_markers
        self.embed_vocab_size = embed_vocab_size
        self.feature_lengths = feature_lengths
        torch.manual_seed(seed)

        super(RelationExtractorCnnPosNetwork, self).__init__()
        self.logger.info("NGram Size is {}".format(ngram_context_size))
        self.dropout_rate = drop_rate
        # Use random weights if vocab size if passed in else load pretrained weights

        self.set_embeddings(None)
        self.embedding_dim = embedding_dim

        self.__pos_embedder__ = pos_embedder

        self.text_column_index = self.feature_lengths.argmax(axis=0)

        self.logger.info("The text feature is index {}, the feature lengths are {}".format(self.text_column_index,
                                                                                           self.feature_lengths))

        # self.windows_sizes = [5, 4, 3, 2, 1]
        self.windows_sizes = [5]

        cnn_stride = 1
        pool_stride = 1

        self.cnn_layers = nn.ModuleList()
        total_cnn_out_size = 0
        # The total embedding size if the text column + position for the rest
        pos_embed_total_dim = 2 * self.pos_embedder.embeddings.shape[1]
        total_dim_size = embedding_dim + pos_embed_total_dim
        self.logger.info(
            "Word embedding size is {}, pos embedding size is {}, cnn_output size {}, total is {}".format(embedding_dim,
                                                                                                          pos_embed_total_dim,
                                                                                                          cnn_output,
                                                                                                          total_dim_size))

        for k in self.windows_sizes:
            layer1_cnn_output = cnn_output
            layer1_cnn_kernel = min(k, sum(feature_lengths))
            layer1_cnn_stride = cnn_stride
            layer1_cnn_padding = layer1_cnn_kernel // 2
            layer1_cnn_out_length = math.ceil(
                (feature_lengths[
                     self.text_column_index] + 2 * layer1_cnn_padding - layer1_cnn_kernel + 1) / layer1_cnn_stride)

            layer1_pool_kernel = int(self.feature_lengths[self.text_column_index])
            layer1_pool_padding = 0
            layer1_pool_stride = pool_stride
            layer1_pool_out_length = math.ceil(
                (layer1_cnn_out_length + 2 * layer1_pool_padding - layer1_pool_kernel + 1) / layer1_pool_stride)

            self.logger.info(
                "Cnn layer  out length = {}, layer_cnn_kernel={}, pool layer length = {}, layer_pool_kernel={}".format(
                    layer1_cnn_out_length,
                    layer1_cnn_kernel,
                    layer1_pool_out_length,
                    layer1_pool_kernel
                ))

            layer1 = nn.Sequential(
                nn.Conv1d(total_dim_size, layer1_cnn_output, kernel_size=layer1_cnn_kernel, stride=layer1_cnn_stride,
                          padding=layer1_cnn_padding),
                # nn.BatchNorm1d(layer1_cnn_output),
                nn.ReLU(),
                nn.MaxPool1d(kernel_size=layer1_pool_kernel, stride=layer1_pool_stride, padding=layer1_pool_padding)
                , nn.Dropout(dropout_rate_cnn)
            )

            self.cnn_layers.append(layer1)
            total_cnn_out_size += layer1_pool_out_length * layer1_cnn_output

        self._class_size = class_size
        # self.fc = nn.Sequential(
        #     nn.Linear(total_cnn_out_size,
        #               fc_layer_size),
        #     nn.ReLU(),
        #     nn.Dropout(dropout_rate_fc),
        #     nn.Linear(fc_layer_size, class_size))

        self.fc = nn.Sequential(
            nn.Linear(total_cnn_out_size,
                      class_size))

    @property
    def embeddings(self):
        if self.__embeddings is None:
            assert self.embed_vocab_size > 0, "Please set the vocab size for using random embeddings "
            self.__embeddings = nn.Embedding(self.embed_vocab_size, self.embedding_dim)
            self.__embeddings.weight.requires_grad = self.fine_tune_embeddings

        return self.__embeddings

    def set_embeddings(self, value):
        self.__embeddings = value
        if self.__embeddings is not None:
            self.__embeddings.weight.requires_grad = self.fine_tune_embeddings

    @property
    def logger(self):
        return logging.getLogger(__name__)

    @property
    def pos_embedder(self):
        self.__pos_embedder__ = self.__pos_embedder__ or PositionEmbedder()
        return self.__pos_embedder__

    def forward(self, features):

        # The input format is tuples of features.. where each item in tuple is a shape feature_len * batch_szie

        # Assume text is when the feature length is max..
        input = features[0]
        self.logger.debug("Executing embeddings")
        embeddings = self.embeddings(input)

        embeddings_with_pos = embeddings
        self.logger.debug("Executing pos embedding")

        for _, entity in enumerate(self.entity_markers):

            # TODO: avoid this loop, use builtin
            batch_pos_embedding_entity = []

            for i, (t, sentence_embedding) in enumerate(zip(input, embeddings)):
                sentence_pos_embedding = self.pos_embedder(t, entity)

                # Set pos_embedding to zero when pad token ( indicated by zero embedding)
                sentence_pos_embedding[torch.all(sentence_embedding.eq(0.0), dim=1)] = 0.0
                batch_pos_embedding_entity.append(sentence_pos_embedding)

            batch_pos_embedding_entity_tensor = torch.stack(batch_pos_embedding_entity).to(
                device=embeddings_with_pos.device)

            embeddings_with_pos = torch.cat([embeddings_with_pos, batch_pos_embedding_entity_tensor], dim=2)

        # Final output
        # Conv1d takes in (batch, channels, seq_len), but raw embedded is (batch, seq_len, channels)
        final_input = embeddings_with_pos.permute(0, 2, 1)

        self.logger.debug("Running through layers")
        outputs = []
        for cnn_layer in self.cnn_layers:
            out1 = cnn_layer(final_input)
            outputs.append(out1)

        out = torch.cat(outputs, dim=2)

        out = out.reshape(out.size(0), -1)

        self.logger.debug("Running fc")
        out = self.fc(out)

        return out
