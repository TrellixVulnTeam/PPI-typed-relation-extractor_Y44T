import logging

from modelnetworks.NetworkFactoryBase import NetworkFactoryBase
from modelnetworks.RelationExtractorBiLstmNetworkNoPos import RelationExtractorBiLstmNetworkNoPos


class RelationExtractorBiLstmNetworkFactoryNoPos(NetworkFactoryBase):

    @property
    def logger(self):
        return logging.getLogger(__name__)

    def _get_value(self, kwargs, key, default):
        value = kwargs.get(key, default)
        self.logger.info("Retrieving key {} with default {}, found {}".format(key, default, value))
        return value

    def get_network(self, class_size, embedding_dim, feature_lens, **kwargs):
        lstm_dropout = float(self._get_value(kwargs, "lstm_dropout", ".5"))

        lstm_num_layers = int(self._get_value(kwargs, "lstm_num_layers", "3"))
        dropout_rate_fc = float(self._get_value(kwargs, "fc_drop_out_rate", ".5"))

        lstm_hidden_size = int(self._get_value(kwargs, "lstm_hidden_size", "64"))

        model = RelationExtractorBiLstmNetworkNoPos(class_size=class_size, embedding_dim=embedding_dim,
                                                    feature_lengths=feature_lens, hidden_size=lstm_hidden_size,
                                                    dropout_rate_fc=dropout_rate_fc, num_layers=lstm_num_layers,
                                                    lstm_dropout=lstm_dropout)

        return model