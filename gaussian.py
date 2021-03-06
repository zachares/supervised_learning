import numpy as np
import torch
import torch.nn.functional as F

def _logprobs(means, prec, samples):
    num_size_dims = len(list(prec.size()))

    if num_size_dims == 1: # univariate
        return 0.5 * (torch.log(prec) - prec * (samples - means).pow(2) - (np.log(2 * np.pi)))
    elif num_size_dims == 2: # diagonal covariance
        return 0.5 * (torch.log(prec) - prec * (samples - means).pow(2) - np.log(2 * np.pi)).sum(-1) 
    # elif num_size_dims == 3: # full covaraince matrix
    #     prec_det = torch.det(prec)

    #     log_prob_const = 0.5 * torch.log(prec_det) - prec.size(1) * np.log(2 * np.pi)
    #     err = (samples - means).unsqueeze(1) 
    #     log_prob_sample = -0.5 * torch.bmm(torch.bmm(err, prec), err.transpose(1,2))

    #     return log_prob_const + log_prob_sample
    else:
        raise Exception("estimates tensor size invalid with number of dimensions" + str(num_size_dims))

def negative_log_likelihood(params, labels):
    means, precs = params
    return -1.0 * _logprobs(means, precs, labels)

def negative_entropy(params, labels):
    means, precs = params
    return 1.0 * _logprobs(means, precs, labels).sum(-1)

def samples2error_metric(params, labels):
    means, precs = params

    num_size_dims = len(list(precs.size()))

    errors = labels - means

    if num_size_dims == 1 or num_size_dims ==2 or num_size_dims ==3:

        if num_size_dims == 1:
            errors_norm = torch.abs(errors)
        else:
            errors_norm = errors.norm(p=2, dim =1)

        if num_size_dims == 1:
            cov_trace_sum = precs.pow(-1)
        elif num_size_dims == 2:
            covtraces_sum = precs.pow(-1).sum(1)
        else:
            covtraces_sum = torch.diagonal(torch.inverse(precs), dim1 = 1, dim2=2).sum(1)

        covtrace_error_ratio = torch.where(errors_norm.pow(2) != 0, (covtraces_sum / errors_norm.pow(2)), torch.zeros_like(errors_norm))

        return errors_norm, covtrace_error_ratio 
    else:
        raise Exception("estimates tensor size invalid with number of dimensions" + str(num_size_dims))

def params2error_metric(input_tuple):
    dis0, dis1 = input_tuple

    means0, precs0 = dis0
    means1, precs1 = dis1

    num_size_dims = len(list(prec0.size()))

    errors = means0 - means1

    if num_size_dims == 1 or num_size_dims ==2 or num_size_dims ==3:

        if num_size_dims == 1:
            errors_norm = torch.abs(errors)
        else:
            errors_norm = errors.norm(p=2, dim =1)

        if num_size_dims == 1:
            cov_trace_sum0 = (1 / prec0)
            cov_trace_sum1 = (1 / prec1)
        elif num_size_dims == 2:
            covtraces_sum0 = (1 / prec0).sum(1)
            covtraces_sum1 = (1 / prec1).sum(1)
        else:
            covtraces_sum0 = torch.diagonal(torch.inverse(precs0), dim1 = 1, dim2=2).sum(1)
            covtraces_sum1 = torch.diagonal(torch.inverse(precs1), dim1 = 1, dim2=2).sum(1)

        covtrace_error_ratio = covtraces_sum0 / covtraces_sum1

        return errors_norm, covtrace_error_ratio
    else:
        raise Exception("estimates tensor size invalid with number of dimensions" + str(num_size_dims))

def divergence_KL(dis0, dis1):
    means0, precs0 = dis0
    means1, precs1 = dis1

    num_size_dims = len(list(precs0.size()))

    if num_size_dims == 1:
        return 0.5 * (torch.log(precs0) - torch.log(precs1) + precs1 / precs0 + precs1 * (means0 - means1).pow(2) - 1)
    elif num_size_dims == 2:
        # prec.prod(1) = determinant of a diagonal precision matrix
        return 0.5 * (torch.log(precs0) - torch.log(precs1) + precs1 / precs0 + precs1 * (means0 - means1).pow(2) - 1).sum(-1)

    elif num_size_dims == 3:
        precs_det0 = torch.det(precs0)
        precs_det1 = torch.det(precs1)

        precs0_inv = torch.inverse(precs0)
        precs_mult = torch.bmm(precs1, precs0_inv)

        precs_mult_trace = torch.diagonal(precs_mult, dim1=1, dim2=2).sum(1)

        mean_error = (mean1 - mean0).unsqueeze(2)

        return 0.5 * (torch.log(precs0_det/precs1_det) + precs_mult_trace + torch.bmm(torch.bmm(mean_error.transpose(1,2), precs1), mean_error).squeeze())
    else:
        raise Exception("estimates tensor size invalid with number of dimensions" + str(num_size_dims))

#### This function needs to checked out
def productofgaussians(mean_vect, prec_vect):
    num_size_dims = len(list(mean_vect.size()))

    if num_size_dims == 2:
        prec = prec_vect.sum(1)
        mean = mean_vect * prec_vect / prec.unsqueeze(1).repeat_interleave(prec_vect.size(1), dim = 1)
        
        return mean, prec
    elif num_size_dims == 3:
        prec = prec_vect.sum(1)

        mean = (mean_vect * prec_vect / prec.unsqueeze(1).repeat_interleave(prec_vect.size(1), dim = 1)).sum(1)

        return mean, prec

    elif num_size_dims == 4:
        prec = prec_vect.sum(1)

        prec_inv_reshape = torch.reshape(torch.inverse(prec).unsqueeze(1).repeat_interleave(prec_vect.size(1), dim = 1), (prec.size(0) * prec_vect.size(1), prec.size(1), prec.size(2)))
        prec_vect_reshape = torch.reshape(prec_vect, (prec_vect.size(0) * prec_vect.size(1), prec_vect.size(2), prec_vect.size(3)))
        prec_mm_reshape = torch.bmm(prec_inv_reshape, prec_vect_reshape)
        mean_vect_reshape = torch.reshape(mean_vect, (mean_vect.size(0) * mean_vect.size(1), mean_vect.size(2), 1))
        mean_unsummed_reshape = torch.bmm(prec_mm_reshape, mean_vect_reshape)
        mean = torch.reshape(mean_unsummed_reshape, (mean_vect.size(0), mean_vect.size(1), mean_vect.size(2))).sum(1)

        return mean, prec   
    else:
        raise Exception("estimates tensor size invalid with number of dimensions" + str(num_size_dims))

def sample(mean, prec, device):
    num_size_dims = len(list(prec.size()))
    
    if num_size_dims == 1 or num_size_dims == 2:
        variance = 1 / (F.softplus(prec) + 1e-8)
        epsilon = Normal(0, 1).sample(mean.size())
        return mean + torch.sqrt(variance) * epsilon.to(device)
    elif num_size_dims == 3:
        raise Exception("precision matrix number of dimensions" + str(num_size_dims) + " not currently supported")        
    else:
        raise Exception("estimates tensor size invalid with number of dimensions" + str(num_size_dims))

def output2params(params):
    num_size_dims = len(list(params.size()))
    if num_size_dims == 2:
        return torch.split(h, h.size(1) // 2, dim=1) 
    else:
        raise Exception("params tensor size invalid with number of dimensions" + str(num_size_dims))

def params2prec(params_matrix): #converting estimated parameters to a multivariate normal's covariance matrix
    m_tril = params_matrix.tril()
    if len(list(params_matrix)) == 2:
        m_tril[torch.arange(m_tril.size(0)), torch.arange(m_tril.size(1))] = torch.abs(torch.diagonal(m_tril, dim1 = 1, dim2=2))
        prec = torch.bmm(m_tril.transpose(1,2).transpose(1,0),m_tril.transpose(1,2).transpose(1,0).transpose(1,2))        
    else:
        m_tril[torch.arange(chol_dec.size(0)), torch.arange(chol_dec.size(1))] = torch.abs(chol_dec.diag())
        prec = torch.mm(m_tril, m_tril.t())

    return prec

def _det3(mats):
    return mats[:,0,0] * (mats[:,1,1] * mats[:,2,2] - mats[:,1,2] *mats[:,2,1]) -\
     mats[:,0,1] * (mats[:,1,0] * mats[:,2,2] - mats[:,2,0] * mats[:,1,2]) +\
      mats[:,0,2] * (mats[:,1,0] * mats[:,2,1] - mats[:,1,1] * mats[:,2,0])
