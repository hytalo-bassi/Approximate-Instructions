
/*============================================================================

This C source file is part of the SoftFloat IEEE Floating-Point Arithmetic
Package, Release 3d, by John R. Hauser.

Copyright 2011, 2012, 2013, 2014, 2015 The Regents of the University of
California.  All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 1. Redistributions of source code must retain the above copyright notice,
    this list of conditions, and the following disclaimer.

 2. Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions, and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

 3. Neither the name of the University nor the names of its contributors may
    be used to endorse or promote products derived from this software without
    specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS "AS IS", AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE, ARE
DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

=============================================================================*/
#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include "platform.h"
#include "internals.h"
#include "specialize.h"
#include "softfloat.h"

//int MULX(int i, int s); 
/*int MULX(int i, int s) // i = i + s
{  
    int MULX;
    asm volatile
    (  
      "mulx   %[z], %[x], %[y]\n\t"
      : [z] "=r" (MULX)
      : [x] "r" (i), [y] "r" (s)
    );
    return (MULX); 
}//end */

float32_t f32_mulx( float32_t a, float32_t b )
{
    union ui32_f32 uA;
    uint_fast32_t uiA;
    uint32_t signA;
    int_fast16_t expA;
    uint_fast32_t sigA;    //mantissa A
    union ui32_f32 uB;
    uint_fast32_t uiB;
    uint32_t signB;
    int_fast16_t expB;
    uint_fast32_t sigB;    //mantissa B
    uint32_t signZ;
    uint_fast32_t magBits;
    struct exp16_sig32 normExpSig;
    int_fast16_t expZ;
    uint_fast32_t sigZ, uiZ;
    union ui32_f32 uZ;
    int_fast16_t expZ_1;
    //int MULT;//instrução divx.h (dissertação)
    

    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
    uA.f = a;
    uiA = uA.ui;
    signA = signF32UI( uiA );
    expA  = expF32UI( uiA );
    sigA  = fracF32UI( uiA ); //mantissa A
    uB.f = b;
    uiB = uB.ui;
    signB = signF32UI( uiB );
    expB  = expF32UI( uiB );
    sigB  = fracF32UI( uiB ); //mantissa B
    //#####################
    signZ = signA ^ signB;
    //#####################
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
    if ( expA == 0xFF ) {
        if ( sigA || ((expB == 0xFF) && sigB) ) goto propagateNaN;
        magBits = expB | sigB;
        goto infArg;
    }
    if ( expB == 0xFF ) {
        if ( sigB ) goto propagateNaN;
        magBits = expA | sigA;
        goto infArg;
    }
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
    if ( ! expA ) {//entendi como uma normalização dos "zeros"
        if ( ! sigA ) goto zero;
        normExpSig = softfloat_normSubnormalF32Sig( sigA );
        expA = normExpSig.exp;
        sigA = normExpSig.sig;
    }                       //softfloat_normSubnormalF32Sig = chama cont de zeros
    if ( ! expB ) {
        if ( ! sigB ) goto zero;
        normExpSig = softfloat_normSubnormalF32Sig( sigB );
        expB = normExpSig.exp;
        sigB = normExpSig.sig;
    }
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
    //************Teste************************
    
    //expZ = expA + expB - 0x7F;//ORIG
      expZ = expA ^ expB - 0x7F;//APPROX
    
    //expZ_1 = expA + expB;//Cenário 5
    //expZ = expZ_1 - 0x7F;
    //expZ = ((~expZ_1 & 0x7F) | (0x7F & 0) | (~expZ_1 & 0) | (expZ_1 & ~0x7F & ~0)); //Cenário 5
    
    
    //********************************************
    sigA = (sigA | 0x00800000)<<7;
    sigB = (sigB | 0x00800000)<<8;
    
    //************Teste************************
    sigZ = softfloat_shortShiftRightJam64x( (uint_fast64_t) sigA * sigB, 32 );//ORIG
    
    /*MULT =  MULX(sigA,sigB);//Cenário 4 - MINHA
    sigZ = softfloat_shortShiftRightJam64( (uint_fast64_t) MULT, 32 );//Cenário 4*/
    //********************************************
    if ( sigZ < 0x40000000 ) { //shortShiftRightJam64 = 1 linha com um sinal de -
        --expZ;
        sigZ <<= 1;
    }
    //************Teste ************************
    //mudei a função s_roundPackToF32.c 
    // C1 e C2
    return softfloat_roundPackToF32x( signZ, expZ, sigZ );
    //********************************************
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
 propagateNaN:
    uiZ = softfloat_propagateNaNF32UI( uiA, uiB );// tem OR
    goto uiZ;
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
 infArg:
    if ( ! magBits ) {
        softfloat_raiseFlags( softfloat_flag_invalid );//seta flag
        uiZ = defaultNaNF32UI;
    } else {
        uiZ = packToF32UI( signZ, 0xFF, 0 );//junta todo mundo
    }
    goto uiZ;
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
 zero:
    uiZ = packToF32UI( signZ, 0, 0 );
 uiZ:
    uZ.ui = uiZ;
    return uZ.f;

}





