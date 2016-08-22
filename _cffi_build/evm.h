/// Host-endian 256-bit integer.
///
/// 32 bytes of data representing host-endian (that means little-endian almost
/// all the time) 256-bit integer. This applies to the words[] order as well.
/// words[0] contains the 64 lowest precision bits, words[3] constains the 64
/// highest precision bits.
struct evm_uint256 {
    /// The 4 64-bit words of the integer. Memory aligned to 8 bytes.
    uint64_t words[4];
};

/// 160-bit hash suitable for keeping an Ethereum address.
struct evm_hash160 {
    /// The 20 bytes of the hash.
    uint8_t bytes[20];
};


/// Big-endian 256-bit integer/hash.
///
/// 32 bytes of data. For EVM that means big-endian 256-bit integer. Values of
/// this type are converted to host-endian values inside EVM.
struct evm_hash256 {
   union {
        /// The 32 bytes of the integer/hash. Memory aligned to 8 bytes.
        uint8_t bytes[32];
        /// Additional access by uint64 words to enforce 8 bytes alignment.
        uint64_t words[4];
   };
};


//#define EVM_EXCEPTION (-9223372036854775807LL -1)  ///< The execution ended with an exception.

/// Complex struct representing execution result.
struct evm_result {
    /// Gas left after execution or exception indicator.
    int64_t gas_left;

    /// Rerefence to output data. The memory containing the output data
    /// is owned by EVM and is freed with evm_destroy_result().
    uint8_t const* output_data;

    /// Size of the output data.
    size_t output_size;

    /// Pointer to EVM-owned memory.
    /// @see output_data.
    void* internal_memory;
};

/// The query callback key.
enum evm_query_key {
    EVM_SLOAD = 0,            ///< Storage value of a given key for SLOAD.
    EVM_ADDRESS = 1,          ///< Address of the contract for ADDRESS.
    EVM_CALLER = 2,           ///< Message sender address for CALLER.
    EVM_ORIGIN = 3,           ///< Transaction origin address for ORIGIN.
    EVM_GAS_PRICE = 4,        ///< Transaction gas price for GASPRICE.
    EVM_COINBASE = 5,         ///< Current block miner address for COINBASE.
    EVM_DIFFICULTY = 6,       ///< Current block difficulty for DIFFICULTY.
    EVM_GAS_LIMIT = 7,        ///< Current block gas limit for GASLIMIT.
    EVM_NUMBER = 8,           ///< Current block number for NUMBER.
    EVM_TIMESTAMP = 9,        ///< Current block timestamp for TIMESTAMP.
    EVM_CODE_BY_ADDRESS = 10, ///< Code by an address for EXTCODE/SIZE.
    EVM_BALANCE = 11,         ///< Balance of a given address for BALANCE.
    EVM_BLOCKHASH = 12        ///< Block hash of by block number for BLOCKHASH.
};


/// Opaque struct representing execution enviroment managed by the host
/// application.
struct evm_env;

/// Variant type to represent possible types of values used in EVM.
///
/// Type-safety is lost around the code that uses this type. We should have
/// complete set of unit tests covering all possible cases.
/// The size of the type is 64 bytes and should fit in single cache line.
union evm_variant {
    /// A host-endian 64-bit integer.
    int64_t int64;

    /// A host-endian 256-bit integer.
    struct evm_uint256 uint256;

    /// A big-endian 256-bit integer/hash.
    struct evm_hash256 hash256;

    struct {
        /// Additional padding to align the evm_variant::address with lower
        /// bytes of a full 256-bit hash.
        uint8_t address_padding[12];

        /// An Ethereum address.
        struct evm_hash160 address;
    };

    /// A memory reference.
    struct {
        /// Pointer to the data.
        uint8_t const* data;

        /// Size of the referenced memory/data.
        size_t data_size;
    };
};

/// Query callback function.
///
/// This callback function is used by the EVM to query the host application
/// about additional data required to execute EVM code.
/// @param env  Pointer to execution environment managed by the host
///             application.
/// @param key  The kind of the query. See evm_query_key and details below.
/// @param arg  Additional argument to the query. It has defined value only for
///             the subset of query keys.
///
/// ## Types of queries
/// Key                   | Arg                  | Expected result
/// ----------------------| -------------------- | ----------------------------
/// ::EVM_GAS_PRICE       |                      | evm_variant::uint256
/// ::EVM_ADDRESS         |                      | evm_variant::address
/// ::EVM_CALLER          |                      | evm_variant::address
/// ::EVM_ORIGIN          |                      | evm_variant::address
/// ::EVM_COINBASE        |                      | evm_variant::address
/// ::EVM_DIFFICULTY      |                      | evm_variant::uint256
/// ::EVM_GAS_LIMIT       |                      | evm_variant::int64
/// ::EVM_NUMBER          |                      | evm_variant::int64?
/// ::EVM_TIMESTAMP       |                      | evm_variant::int64?
/// ::EVM_CODE_BY_ADDRESS | evm_variant::address | evm_variant::bytes
/// ::EVM_BALANCE         | evm_variant::address | evm_variant::uint256
/// ::EVM_BLOCKHASH       | evm_variant::int64   | evm_variant::uint256
/// ::EVM_SLOAD           | evm_variant::uint256 | evm_variant::uint256?
typedef union evm_variant (*evm_query_fn)(struct evm_env* env,
                                          enum evm_query_key key,

                                         union evm_variant arg);
/// The update callback key.
enum evm_update_key {
    EVM_SSTORE = 0,        ///< Update storage entry
    EVM_LOG = 1,           ///< Log.
    EVM_SELFDESTRUCT = 2,  ///< Mark contract as selfdestructed and set
                           ///  beneficiary address.
};


/// Callback function for modifying a contract state.
typedef void (*evm_update_fn)(struct evm_env* env,
                              enum evm_update_key key,
                              union evm_variant arg1,
                              union evm_variant arg2);

/// The kind of call-like instruction.
enum evm_call_kind {
    EVM_CALL = 0,         ///< Request CALL.
    EVM_DELEGATECALL = 1, ///< Request DELEGATECALL. The value param ignored.
    EVM_CALLCODE = 2,     ///< Request CALLCODE.
    EVM_CREATE = 3        ///< Request CREATE. Semantic of some params changes.
};

/// Pointer to the callback function supporting EVM calls.
///
/// @param env          Pointer to execution environment managed by the host
///                     application.
/// @param kind         The kind of call-like opcode requested.
/// @param gas          The amount of gas for the call.
/// @param address      The address of a contract to be called. Ignored in case
///                     of CREATE.
/// @param value        The value sent to the callee. The endowment in case of
///                     CREATE.
/// @param input        The call input data or the create init code.
/// @param input_size   The size of the input data.
/// @param output       The reference to the memory where the call output is to
///                     be copied. In case of create, the memory is guaranteed
///                     to be at least 160 bytes to hold the address of the
///                     created contract.
/// @param output_data  The size of the output data. In case of create, expected
///                     value is 160.
/// @return      If non-negative - the amount of gas left,
///              If negative - an exception occurred during the call/create.
///              There is no need to set 0 address in the output in this case.
typedef int64_t (*evm_call_fn)(
    struct evm_env* env,
    enum evm_call_kind kind,
    int64_t gas,
    struct evm_hash160 address,
    struct evm_uint256 value,
    uint8_t const* input,
    size_t input_size,
    uint8_t* output,
    size_t output_size);

/// A piece of information about the EVM implementation.
enum evm_info_key {
    EVM_NAME  = 0,   ///< The name of the EVM implementation. ASCII encoded.
    EVM_VERSION = 1  ///< The software version of the EVM.
};

/// Request information about the EVM implementation.
///
/// @param key  What do you want to know?
/// @return     Requested information as a c-string. Nonnull.
char const* evm_get_info(enum evm_info_key key);

/// Opaque type representing a EVM instance.
struct evm_instance;

/// Creates new EVM instance.
///
/// Creates new EVM instance. The instance must be destroyed in evm_destroy().
/// Single instance is thread-safe and can be shared by many threads. Having
/// **multiple instances is safe but discouraged** as it has not benefits over
/// having the singleton.
///
/// @param query_fn   Pointer to query callback function. Nonnull.
/// @param update_fn  Pointer to update callback function. Nonnull.
/// @param call_fn    Pointer to call callback function. Nonnull.
/// @return           Pointer to the created EVM instance.
struct evm_instance* evm_create(evm_query_fn query_fn,
                                       evm_update_fn update_fn,
                                       evm_call_fn call_fn);

// struct evm_instance* evm_create_wr(evm_query_ptr eq, evm_update_ptr eu, evm_call_fn ec);

/// Destroys the EVM instance.
///
/// @param evm  The EVM instance to be destroyed.
void evm_destroy(struct evm_instance* evm);


/// Configures the EVM instance.
///
/// Allows modifying options of the EVM instance.
/// Options:
/// - code cache behavior: on, off, read-only, ...
/// - optimizations,
///
/// @param evm    The EVM instance to be configured.
/// @param name   The option name. Cannot be null.
/// @param value  The new option value. Cannot be null.
/// @return       True if the option set successfully.
unsigned char evm_set_option(struct evm_instance* evm,
                           char const* name,
                           char const* value);


/// EVM compatibility mode aka chain mode.
/// TODO: Can you suggest better name?
enum evm_mode {
    EVM_FRONTIER = 0,
    EVM_HOMESTEAD = 1
};


/// Generates and executes machine code for given EVM bytecode.
///
/// All the fun is here. This function actually does something useful.
///
/// @param instance    A EVM instance.
/// @param env         A pointer to the execution environment provided by the
///                    user and passed to callback functions.
/// @param mode        EVM compatibility mode.
/// @param code_hash   A hash of the bytecode, usually Keccak. The EVM uses it
///                    as the code identifier. A EVM implementation is able to
///                    hash the code itself if it requires it, but the host
///                    application usually has the hash already.
/// @param code        Reference to the bytecode to be executed.
/// @param code_size   The length of the bytecode.
/// @param gas         Gas for execution. Min 0, max 2^63-1.
/// @param input       Reference to the input data.
/// @param input_size  The size of the input data.
/// @param value       Call value.
/// @return            All execution results.
struct evm_result evm_execute(struct evm_instance* instance,
                                     struct evm_env* env,
                                     enum evm_mode mode,
                                     struct evm_hash256 code_hash,
                                     uint8_t const* code,
                                     size_t code_size,
                                     int64_t gas,
                                     uint8_t const* input,
                                     size_t input_size,
                                     struct evm_uint256 value);

/// Destroys execution result.
void evm_destroy_result(struct evm_result);


/// @defgroup EVMJIT EVMJIT extenstion to EVM-C
/// @{


unsigned char evmjit_is_code_ready(struct evm_instance* instance, enum evm_mode mode,
                                 struct evm_hash256 code_hash);

void evmjit_compile(struct evm_instance* instance, enum evm_mode mode,
                           uint8_t const* code, size_t code_size,
                           struct evm_hash256 code_hash);

/// @}
