import torch.nn.init as init
from torch import nn
import torch
from torch.nn import functional as F

class TransformerEncoder(nn.Module):
    '''Transformer encoder module for sequence data'''
    def __init__(self, input_dim, d_model, nhead, num_layers, dim_feedforward=128, mean=False):
        super().__init__()
        self.mean = mean
        self.linear_in = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)
        
    def forward(self, x):
        """
        x: Input tensor with shape [batch_size, seq_len, input_dim]
        """
        # Linear mapping to d_model dimension
        x = self.linear_in(x)
        # Pass through Transformer encoder
        output = self.transformer_encoder(x)
        # Take the mean along the sequence dimension as feature representation
        
        if self.mean:
            output = torch.mean(output, dim=1)
        return output


class RefuelingVehicleModel(nn.Module):
    """Refueling vehicle information fusion model"""
    def __init__(
        self, 
        tanker_dim=2, 
        am_dim=6, 
        time_dim=1,
        d_model=64, 
        nhead=2, 
        num_layers=2,
        mlp_hidden_dim=128,
        output_dim=5
    ):
        super().__init__()
        
        # Transformer encoder for refueling vehicle information
        self.tanker_encoder = TransformerEncoder(
            input_dim=tanker_dim,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers,
            dim_feedforward=128,
            mean=True
        )
        
        # Transformer encoder for agricultural machine information
        self.machine_encoder = TransformerEncoder(
            input_dim=am_dim,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers,
            dim_feedforward=128,
            mean=True
        )
        
        # MLP output layer
        self.mlp = nn.Sequential(
            nn.Linear(d_model + d_model + 1, mlp_hidden_dim),
            nn.ReLU(),
            nn.Linear(mlp_hidden_dim, mlp_hidden_dim),
            nn.ReLU(),
            nn.Linear(mlp_hidden_dim, output_dim)
        )

    def forward(self, state_pack, mask=None, future_info=None):
        """
        tankers: Information of other refueling vehicles, shape [batch_size, num_tankers, tanker_dim]
        tractors: Agricultural machine information, shape [batch_size, num_tractors, tractor_dim]
        time: Time variable, shape [batch_size, time_dim]
        """
        
        tankers, machines, time = state_pack
        
        # Encode refueling vehicle information
        tanker_features = self.tanker_encoder(tankers)
        
        # Encode agricultural machine information
        tractor_features = self.machine_encoder(machines)
        
        # Process time features
        time_features = time
        
        # Concatenate all features
        combined_features = torch.cat([tanker_features, tractor_features, time_features], dim=1)
        
        
        # Generate output through MLP
        q_values = self.mlp(combined_features)
        if mask is not None:
            q_values = q_values.masked_fill(mask, float('-inf'))
            
        probs = F.softmax(q_values, dim=-1)    
            
        return probs



class MatchingModel(nn.Module):
    """Matching model for refueling vehicles and agricultural machines"""
    def __init__(
        self, 
        tanker_dim=5,        # Feature dimension of refueling vehicles
        tractor_dim=8,       # Feature dimension of agricultural machines (including virtual orders)
        extra_dim=1,         # Pair extra feature dimension (replaced time_dim)
        d_model=64,          # Transformer hidden dimension
        nhead=2,             # Number of Transformer attention heads
        num_layers=2,        # Number of Transformer layers
        mlp_hidden_dim=128,  # MLP hidden layer dimension
    ):
        super().__init__()
        
        # Transformer encoder for refueling vehicle information
        self.tanker_encoder = TransformerEncoder(
            input_dim=tanker_dim,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers
        )
        
        # Transformer encoder for agricultural machine information
        self.tractor_encoder = TransformerEncoder(
            input_dim=tractor_dim,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers
        )
        
        # MLP for generating matching scores - input dimension adjusted to d_model*2 + extra_dim
        self.mlp_matcher = nn.Sequential(
            nn.Linear(d_model * 2 + extra_dim, mlp_hidden_dim),  # Concatenate pair extra features
            nn.ReLU(),
            nn.Linear(mlp_hidden_dim, mlp_hidden_dim),
            nn.ReLU(),
            nn.Linear(mlp_hidden_dim, 1)  # Output matching score
        )
        
    def forward(self, state_pack, mask=None):
        """
        tankers: Refueling vehicle information, shape [batch_size, num_tankers, tanker_dim]
        tractors: Agricultural machine information (including virtual orders), shape [batch_size, num_tractors+1, tractor_dim]
        pair_extra_features: Extra features for pairs, shape [batch_size, num_tankers * num_tractors, extra_dim]
        """
        
        tankers, tractors, pair_extra_features = state_pack
        batch_size = tankers.shape[0]
        num_tankers = tankers.shape[1]
        num_tractors = tractors.shape[1]  # Includes virtual orders
        
        # Encode refueling vehicle information
        # [batch_size, num_tankers, d_model]
        tanker_features = self.tanker_encoder(tankers)
        
        # Encode agricultural machine information
        # [batch_size, num_tractors, d_model]
        tractor_features = self.tractor_encoder(tractors)
        
        # Create all possible refueling vehicle-agricultural machine pairs
        # [batch_size, num_tankers, 1, d_model]
        tanker_features_expanded = tanker_features.unsqueeze(2)
        # [batch_size, 1, num_tractors, d_model]
        tractor_features_expanded = tractor_features.unsqueeze(1)
        
        # Expand features to match dimensions
        # [batch_size, num_tankers, num_tractors, d_model]
        tanker_features_expanded = tanker_features_expanded.expand(
            -1, -1, num_tractors, -1
        )
        tractor_features_expanded = tractor_features_expanded.expand(
            -1, num_tankers, -1, -1
        )
        
        # Flatten the expanded features to concatenate with pair_extra_features
        # [batch_size, num_tankers * num_tractors, d_model]
        tanker_features_flat = tanker_features_expanded.reshape(batch_size, -1, tanker_features.size(-1))
        tractor_features_flat = tractor_features_expanded.reshape(batch_size, -1, tractor_features.size(-1))
        
        # Concatenate features: [refueling vehicle features, agricultural machine features, pair extra features]
        # [batch_size, num_tankers * num_tractors, d_model*2 + extra_dim]
        pair_features = torch.cat([
            tanker_features_flat,
            tractor_features_flat,
            pair_extra_features
        ], dim=-1)
        
        # Compute matching scores through MLP
        # [batch_size, num_tankers*num_tractors, 1]
        match_scores_flat = self.mlp_matcher(pair_features)
        
        # Reshape to [batch_size, num_tankers * num_online tractors]
        match_scores = match_scores_flat.squeeze(-1)
        
        if mask is not None:
            match_scores = match_scores.masked_fill(mask, float('-inf'))
        
        # Apply Softmax to get probabilities
        probs = F.softmax(match_scores, dim=-1)
        
        return probs