# linux-memavailable-python
A python backport of the /proc/meminfo "MemAvailable" metric which was introduced in the Linux 3.14 kernel.

This module provides a single python function that uses information
available to users in pre-3.14 kernels to calculate the "MemAvailable"
metric which was introduced in Linux 3.14 kernels.

For a simple command line test, you can do this:
    python -c 'import linux_memavailable; print(linux_memavailable.linux_memavailable())'

Linus Torvalds' explanation of the algorithm and the C code can be
found here:
 https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=34e431b0ae398fc54ea69ff85ec700722c9da773

A more conservative estimate was later implemented:
 https://github.com/torvalds/linux/commit/84ad5802a33a4964a49b8f7d24d80a214a096b19

This implementation implements exactly the algorithm above.

Note: in the very latest kernel source as of 2018-06-20, the algorithm is
almost unchanged except for addition of some amount of memory
considered releasable by the (latest) kernel:
 https://github.com/torvalds/linux/blob/b5d903c2d656e9bc54bc76554a477d796a63120d/mm/page_alloc.c#L4701

This implementation omits that extra bit of kernel-releasable memory.

This python implementation owes much to the Perl implementation by Ivan
Zahariev (famzah): https://github.com/famzah/linux-memavailable-procfs
