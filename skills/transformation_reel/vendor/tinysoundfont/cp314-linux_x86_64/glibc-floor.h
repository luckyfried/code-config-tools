/* Bind the math calls to their oldest x86_64 glibc versions so the module loads on older systems. */
__asm__(".symver log10f,log10f@GLIBC_2.2.5");
__asm__(".symver expf,expf@GLIBC_2.2.5");
__asm__(".symver logf,logf@GLIBC_2.2.5");
__asm__(".symver powf,powf@GLIBC_2.2.5");
__asm__(".symver pow,pow@GLIBC_2.2.5");
