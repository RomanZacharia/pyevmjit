evm_query_ptr geq=0;
evm_update_ptr geu=0;
union evm_variant evm_query_wr(struct evm_env* env,
                                          enum evm_query_key key,
                                          union evm_variant arg)
{
    union evm_variant ret;
    geq(env, key, &arg, &ret);
    return ret;
}
void evm_update_wr(struct evm_env* env,
                              enum evm_update_key key,
                              union evm_variant arg1,
                              union evm_variant arg2)
{
    geu(env, key, &arg1, &arg2);
}
struct evm_instance* evm_create_wr(evm_query_ptr eq, evm_update_ptr eu, evm_call_fn ec)
{
    geq = eq;
    geu = eu;
    return evm_create(evm_query_wr, evm_update_wr, ec);
}
