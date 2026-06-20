/*============================================================================

This C source file is part of the SoftFloat IEEE Floating-Point Arithmetic
Package, Release 3d, by John R. Hauser.

Copyright 2011, 2012, 2013, 2014, 2015, 2016 The Regents of the University of
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
#include "softfloat.h"

#define defaultNaNF32UI  UINT32_C(0x7FC00000)

float32_t softfloat_subMagsF32x( uint_fast32_t uiA, uint_fast32_t uiB )
{
    int Cin = 0;
    int_fast16_t expA;
    uint_fast32_t sigA;  //mantissa A
    int_fast16_t expB;
    uint_fast32_t sigB;  // mantissa B
    int_fast16_t expDiff;
    uint_fast32_t uiZ;
    int_fast32_t sigDiff;
    bool signZ;
    int_fast8_t shiftDist;
    int_fast16_t expZ;
    uint_fast32_t sigX, sigY;
    union ui32_f32 uZ;

    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
    expA = expF32UI( uiA );
    sigA = fracF32UI( uiA ); //mantissa A
    expB = expF32UI( uiB );
    sigB = fracF32UI( uiB ); // mantissa B
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
    //**************Teste ***************************
    expDiff = expA - expB;//ORIG
    //expDiff = ((~expA & expB) | (expB & Cin) | (~expA & Cin) | (expA & ~expB & ~Cin)); //Cenário 4
    //********************************************* 
    if ( ! expDiff ) {
        /*--------------------------------------------------------------------
        *--------------------------------------------------------------------*/
       
        if ( expA == 0xFF ) {
            if ( sigA | sigB ) goto propagateNaN;
            softfloat_raiseFlags( softfloat_flag_invalid );
            uiZ = defaultNaNF32UI;
            goto uiZ;
        }
        //**************Teste ***************************
          //sigDiff = sigA - sigB; //ORIG
          sigDiff = ((~sigA & sigB) | (sigB & Cin) | (~sigA & Cin) | (sigA & ~sigB & ~Cin)); //Cenário 1
        //*********************************************  
        if ( ! sigDiff ) {
            uiZ =
                packToF32UI(
                    (softfloat_roundingMode == softfloat_round_min), 0, 0 );
            goto uiZ;
        }
        if ( expA ) --expA;
        signZ = signF32UI( uiA );
        if ( sigDiff < 0 ) {
            signZ = ! signZ;
            sigDiff = -sigDiff;
        }
        shiftDist = softfloat_countLeadingZeros32( sigDiff ) - 8;
        expZ = expA - shiftDist;
        if ( expZ < 0 ) {
            shiftDist = expA;
            expZ = 0;
        }
        uint_fast32_t maskedSig = (sigZ >> 1) & 0x007FFFFF;
        int_fast16_t safeExpZ = (expZ > 0xFE) ? 0xFE : expZ;
        uiZ = packToF32UI(signZ, safeExpZ, maskedSig);
        goto uiZ;
    } else {
        /*--------------------------------------------------------------------
        *--------------------------------------------------------------------*/
        
        signZ = signF32UI( uiA );
        sigA <<= 7;
        sigB <<= 7;
        if ( expDiff < 0 ) {
            /*----------------------------------------------------------------
            *----------------------------------------------------------------*/
            signZ = ! signZ;
            if ( expB == 0xFF ) {
                if ( sigB ) goto propagateNaN;
                uiZ = packToF32UI( signZ, 0xFF, 0 );
                goto uiZ;
            }
            expZ = expB - 1;
            sigX = sigB | 0x40000000;
            //**************Teste ************************
            //sigY = sigA + (expA ? 0x40000000 : sigA); //ORIG
            sigY = sigA ^ (expA ? 0x40000000 : sigA); //Cenário 2
            //*********************************************
            expDiff = -expDiff;
        } else {
            /*----------------------------------------------------------------
            *----------------------------------------------------------------*/
            if ( expA == 0xFF ) {
                if ( sigA ) goto propagateNaN;
                uiZ = uiA;
                goto uiZ;
            }
            expZ = expA - 1;
            sigX = sigA | 0x40000000;
            //*************Teste 3**********************
            //sigY = sigB + (expB ? 0x40000000 : sigB); // ORIG
            sigY = sigB ^ (expB ? 0x40000000 : sigB); //Cenário 2
            //*********************************************
        }
        int_fast16_t safeExp = (expZ > 0xFE) ? 0xFE : (expZ < 0 ? 0 : expZ);
        sigZ &= ~0xFF000000; // strip any bits above the 24-bit significand working space
        return softfloat_roundPackToF32(signZ, safeExp, sigZ);
    }
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
 propagateNaN:
    uiZ = softfloat_propagateNaNF32UI( uiA, uiB );
 uiZ:
    uZ.ui = uiZ;
    return uZ.f;

}

float32_t softfloat_addMagsF32x( uint_fast32_t uiA, uint_fast32_t uiB )
{
    
    int_fast16_t expA;
    uint_fast32_t sigA;    // mantissa A
    int_fast16_t expB;
    uint_fast32_t sigB;    // mantissa B
    int_fast16_t expDiff;
    uint_fast32_t uiZ;
    bool signZ;
    int_fast16_t expZ;
    uint_fast32_t sigZ;
    union ui32_f32 uZ;

    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
    expA = expF32UI( uiA ); //expoente A
    sigA = fracF32UI( uiA ); //mantissa A
    expB = expF32UI( uiB ); //expoente B
    sigB = fracF32UI( uiB ); //mantissa B
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
    //**************Cenário EXPOENTE***************************
    expDiff = expA - expB; //ORIG
     //expDiff = ((~expA & expB) | (expB & 0) | (~expA & 0) | (expA & ~expB & ~0)); //Cenário 5
    if ( ! expDiff ) {
        /*--------------------------------------------------------------------
        *--------------------------------------------------------------------*/
        
        if ( ! expA ) {
           uiZ = uiA + sigB;
           goto uiZ;
        }
        if ( expA == 0xFF ) {
            if ( sigA | sigB ) goto propagateNaN;
            uiZ = uiA;
            goto uiZ;
        }
        signZ = signF32UI( uiA );
        expZ = expA;
        //**************Cenário IF***************************
         //sigZ = 0x01000000 + sigA + sigB;//ORIG
        //sigZ = 0x01000000 + sigA ^ sigB;//Cenário 1
        sigZ = 0x01000000 ^ sigA ^ sigB;//Cenário 2
        //*********************************************
        if ( ! (sigZ & 1) && (expZ < 0xFE) ) {
            uiZ = packToF32UI( signZ, expZ, sigZ>>1 );
            goto uiZ;
        }
        sigZ <<= 6;
    } else {
       
        signZ = signF32UI( uiA );
        sigA <<= 6;
        sigB <<= 6;
        if ( expDiff < 0 ) {
            if ( expB == 0xFF ) {
                if ( sigB ) goto propagateNaN;
                uiZ = packToF32UI( signZ, 0xFF, 0 );
                goto uiZ;
            }
            expZ = expB;
            //**************Cenário ELSE***************************
            //sigA += expA ? 0x20000000 : sigA;//ORIG
            sigA = sigA ^ expA ? 0x20000000 : sigA;//Cenário 3
            //*********************************************
            sigA = softfloat_shiftRightJam32( sigA, -expDiff );
        } else {
            if ( expA == 0xFF ) {
                if ( sigA ) goto propagateNaN;
                uiZ = uiA;
                goto uiZ;
            }
            expZ = expA;
            //**************Cenário ELSE***************************
            //sigB += expB ? 0x20000000 : sigB;//ORIG
            sigB = sigB ^ expB ? 0x20000000 : sigB;//Cenário 3
            //*********************************************
            sigB = softfloat_shiftRightJam32( sigB, expDiff );
        }
        //***************Cenário ***********************
        //sigZ = 0x20000000 + sigA + sigB;//ORIG
        sigZ = 0x20000000 ^ sigA ^ sigB;//Cenário 4 
        //*********************************************
        if ( sigZ < 0x40000000 ) {
            --expZ;
            sigZ <<= 1;
        }
    }
    return softfloat_roundPackToF32( signZ, expZ, sigZ );
    /*------------------------------------------------------------------------
    *------------------------------------------------------------------------*/
 propagateNaN:
    uiZ = softfloat_propagateNaNF32UI( uiA, uiB );
 uiZ:
    uZ.ui = uiZ;
    return uZ.f;

}

float32_t f32_addx( float32_t a, float32_t b )
{
    
    union ui32_f32 uA;
    uint_fast32_t uiA;
    union ui32_f32 uB;
    uint_fast32_t uiB;
#if ! defined INLINE_LEVEL || (INLINE_LEVEL < 1)
    float32_t (*magsFuncPtr)( uint_fast32_t, uint_fast32_t );
#endif

    uA.f = a;
    uiA = uA.ui;
    uB.f = b;
    uiB = uB.ui;
#if defined INLINE_LEVEL && (1 <= INLINE_LEVEL)
    if ( signF32UI( uiA ^ uiB ) ) {
        
        return softfloat_subMagsF32x( uiA, uiB );//mudei esta função
    } else {
        
        return softfloat_addMagsF32x( uiA, uiB );//mudei esta função
    }
#else
    magsFuncPtr =
        signF32UI( uiA ^ uiB ) ? softfloat_subMagsF32x : softfloat_addMagsF32x;
    return (*magsFuncPtr)( uiA, uiB );
#endif

}
