from Levenshtein import ratio

def get_more_similar_prefix(p, prefixes):

    max_similarity = -1
    similar_prefix = prefixes[0]

    for cur_pref in prefixes:
        similarity = ratio(p, cur_pref)
        if similarity > max_similarity:
            similar_prefix = cur_pref
    
    return similar_prefix