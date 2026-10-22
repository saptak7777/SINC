.intel_syntax noprefix
.text

.global __sinc_host_mmap
__sinc_host_mmap:
    mov rdi, 0x20000000
    mov rsi, rcx
    mov rdx, 3
    mov rcx, 50
    mov r8, -1
    mov r9, 0
    sub rsp, 8
    call mmap
    add rsp, 8
    ret

.global __sinc_host_open
__sinc_host_open:
    mov rdi, rax
    mov rsi, rcx
    mov edx, 420
    sub rsp, 8
    call open
    add rsp, 8
    ret

.global __sinc_host_sys_open_read
__sinc_host_sys_open_read:
    mov rdi, rax
    xor esi, esi
    xor edx, edx
    sub rsp, 8
    call open
    add rsp, 8
    ret

.global __sinc_host_sys_open_write
__sinc_host_sys_open_write:
    mov rdi, rax
    mov esi, 577
    mov edx, 420
    sub rsp, 8
    call open
    add rsp, 8
    ret

.global __sinc_host_read
__sinc_host_read:
    mov rdi, rax
    mov rsi, rcx
    sub rsp, 8
    call read
    add rsp, 8
    ret

.global __sinc_host_write
__sinc_host_write:
    mov rdi, rax
    mov rsi, rcx
    sub rsp, 8
    call write
    add rsp, 8
    ret

.global __sinc_host_close
__sinc_host_close:
    mov rdi, rax
    sub rsp, 8
    call close
    add rsp, 8
    ret

.global __sinc_host_exit
__sinc_host_exit:
    mov rdi, rax
    sub rsp, 8
    call exit
    add rsp, 8
    ret

.global __sinc_host_sin
__sinc_host_sin:
    jmp sin

.global __sinc_host_cos
__sinc_host_cos:
    jmp cos

.global __sinc_host_tan
__sinc_host_tan:
    jmp tan

.global __sinc_host_sqrt
__sinc_host_sqrt:
    jmp sqrt

.global __sinc_host_pow
__sinc_host_pow:
    jmp pow

.global __sinc_host_abs
__sinc_host_abs:
    jmp abs

.section .bss
.align 8
sinc_argv_ptr:
    .zero 8

.section .text
.global main
main:
    mov rax, rdi
    mov rcx, rsi
    lea r11, [rip + sinc_argv_ptr]
    mov [r11], rsi
    sub rsp, 8
    call main_sinc
    add rsp, 8
    ret

.global __sinc_host_get_argv
__sinc_host_get_argv:
    lea rax, [rip + sinc_argv_ptr]
    mov rax, [rax]
    ret

.global print_symbol_table_full
print_symbol_table_full:
    ret
