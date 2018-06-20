"""A python function that uses statistics available to users in
pre-3.14 kernels to calculate the "MemAvailable" metric which was
introduced in Linux 3.14 kernels.  Linus Torvalds' explanation of the
algorithm and the C code can be found here:

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
"""

__author__ = "Glenn Horton-Smith"


from mmap import PAGESIZE

def linux_memavailable():
    """Estimate the amount of memory available for userspace allocations,
    without causing swapping. Pure python implementation of the Linux
    algorithm introduced in the 3.14 kernel.
    """
    #-- find the sum of all reserved low watermarks for all zones
    wmark_low, totalreserve = calc_wmark_low_and_totalreserve_pages()
    wmark_low = (wmark_low * PAGESIZE) // 1024
    totalreserve = (totalreserve * PAGESIZE) // 1024
    #-- get the MemFree, Active(file), Inactive(file), and SReclaimable values
    meminfo = {"MemFree" : 0,
               "Active(file)" : 0,
               "Inactive(file)" : 0,
               "SReclaimable" : 0}
    for line in open("/proc/meminfo"):
        info = line.split(None, 2)
        if len(info) == 3:
            key = info[0][:-1]
            if key in meminfo:
                meminfo[key] = int(info[1])
    #-- Start with "MemFree" minus low watermark
    #   "Free memory cannot be taken below the low watermark, before the
    #   system starts swapping."
    available = meminfo["MemFree"] - totalreserve
    #-- Add in the reclaimable page cache
    #   "Not all the page cache can be freed, otherwise the system will
    #   start swapping. Assume at least half of the page cache, or the
    #   low watermark worth of cache, needs to stay."
    pagecache = meminfo["Active(file)"] + meminfo["Inactive(file)"]
    pagecache -= min(pagecache//2, wmark_low)
    available += pagecache
    #-- Add in reclaimable swap ("SReclaimable")
    #   "Part of the reclaimable swap consists of items that are in use,
    #   and cannot be freed. Cap this estimate at the low watermark."
    slab_reclaimable = meminfo["SReclaimable"]
    available += slab_reclaimable - min(slab_reclaimable//2, wmark_low)
    #-- Make non-negative for compatibility
    if available < 0:
        available = 0
    return available


def calc_wmark_low_and_totalreserve_pages():
    """Calculate sum of low watermarks and total reserved space over all
    zones, and return those two values.  Values are in pages.
    """
    fzoneinfo = open("/proc/zoneinfo")
    wmark_low = 0
    totalreserve = 0
    keep_reading = True
    while keep_reading:
        keep_reading = False
        managed = 0
        high = 0
        max_lowmem_reserve = 0
        #-- loop over lines in zone
        for line in fzoneinfo:
            #-- new zone encountered if line starts with "Node"
            if line.startswith("Node"):
                keep_reading = True
                break
            info = line.split(None, 1)
            if len(info) >= 2:
                if info[0] == 'low':
                    wmark_low += int(info[1])
                elif info[0] == 'high':
                    high = int(info[1])
                elif info[0] == 'managed':
                    managed = int(info[1])
                elif info[0] == 'protection:':
                    lowmem_reserve = list(
                        int(l) for l in info[1].strip('()\n ').split(','))
                    max_lowmem_reserve = max(lowmem_reserve)
        #-- calculate reserved pages for this zone according to algorithm
        #   https://github.com/torvalds/linux/blob/6aa303defb7454a2520c4ddcdf6b081f62a15890/mm/page_alloc.c#L6559
        reserve = max_lowmem_reserve + high
        if reserve > managed:
            reserve = managed
        totalreserve += reserve
    return wmark_low, totalreserve
