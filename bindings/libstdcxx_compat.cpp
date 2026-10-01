#include <new>

// Sysal's CentOS 7 release archive is compiled with GCC 11. Some of its object
// files reference this GCC 11 libstdc++ helper even though the public ABI only
// requires older GLIBCXX symbol versions. CentOS 7's runtime does not provide
// the helper, so supply its allocation-failure behavior inside the extension.
extern "C" [[noreturn]] void systemcard_throw_bad_array_new_length()
    __asm__("_ZSt28__throw_bad_array_new_lengthv");

extern "C" [[noreturn]] void systemcard_throw_bad_array_new_length()
{
    throw std::bad_alloc();
}
