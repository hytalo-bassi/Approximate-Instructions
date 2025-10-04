// This instruction is incomplete. In the near future we are going to 
// implement it properly, but now we will just import the addx WRITE_RD

// //Remx - 64X32
// //Line 0 - Quoc 31

// //Block 0 
// reg_t Bin = 0;
// reg_t Q = 0;

// reg_t Bout0 = ((~(x31 ^ (y0 ^ Q)) & Bin) | (~x31 & (y0 ^ Q)));

// reg_t R0 = ((~x31 & (y0 ^ Q)) | ((y0 ^ Q) & Bin) | (~x31 & Bin) | (x31 & ~(y0 ^ Q) & ~Bin));
// .
// .
// .
// //Block 31
// reg_t Bin = Bout30;
// reg_t Q = 0;
// reg_t Bout31 = ((~(x62 ^ (y31 ^ Q)) & Bin) | (~x62 & (y31 ^ Q)));
// reg_t R31 = ((~x62 & (y31 ^ Q)) | ((y31 ^ Q) & Bin) | (~x62 & Bin) | (x62 & ~(y31 ^ Q) & ~Bin));

// reg_t Quoc31 = ~(x63 ^ Bout31 ^ Q);
// reg_t Q = (x63 ^ Bout31 ^ Q);
// reg_t Bin = Q;
// .
// .
// .
// //Line 31 - Quoc 0

// //Block 992 
// reg_t Bout992 = ((~(x0 ^ (y0 ^ Q)) & Bin) | (~x0 & (y0 ^ Q)));
// reg_t R992 = ((~x0 & (y0 ^ Q)) | ((y0 ^ Q) & Bin) | (~x0 & Bin) | (x0 & ~(y0 ^ Q) & ~Bin));
// .
// .
// .
// //Block 1023
// reg_t Bout1023 = ((~(R990 ^ (y31 ^ Q)) & Bin) | (~R990 & (y31 ^ Q)));

// reg_t R1023 = ((~R990 & (y31 ^ Q)) | ((y31 ^ Q) & Bin) | (~R990 & Bin) | (R990 & ~(y31 ^ Q) & ~Bin));

// reg_t Quoc0 = ~(R991 ^ Bout1023 ^ Q);
// .
// .
// .
// //Remainder Correction Circuit
// correct0 <= y0 & Quoc0;
// correct1 <= y1 & Quoc0;
// correct2 <= y2 & Quoc0;
// correct3 <= y3 & Quoc0;
// correct4 <= y4 & Quoc0;
// correct5 <= y5 & Quoc0;
// correct6 <= y6 & Quoc0;
// correct7 <= y7 & Quoc0;
// correct8 <= y8 & Quoc0;
// correct9 <= y9 & Quoc0;
// correct10 <= y10 & Quoc0;
// correct11 <= y11 & Quoc0;
// correct12 <= y12 & Quoc0;
// correct13 <= y13 & Quoc0;
// correct14 <= y14 & Quoc0;
// correct15 <= y15 & Quoc0;
// correct16 <= y16 & Quoc0;
// correct17 <= y17 & Quoc0;
// correct18 <= y18 & Quoc0;
// correct19 <= y19 & Quoc0;
// correct20 <= y20 & Quoc0;
// correct21 <= y21 & Quoc0;
// correct22 <= y22 & Quoc0;
// correct23 <= y23 & Quoc0;
// correct24 <= y24 & Quoc0;
// correct25 <= y25 & Quoc0;
// correct26 <= y25 & Quoc0;
// correct27 <= y27 & Quoc0;
// correct28 <= y28 & Quoc0;
// correct29 <= y29 & Quoc0;
// correct30 <= y30 & Quoc0;
// correct31 <= y31 & Quoc0;

// reg_t Bin = 1;
// reg_t Q = 1;

// //Line Correction - Remainder

// //Block 1024 
// reg_t Bout1024 = ((~(R992 ^ (correct0 ^ Q)) & Bin) | (~R992 & ((correct0  ^ Q)));
// reg_t Rem0 = ((~R992 & ((correct0  ^ Q)) | (((correct0  ^ Q) & Bin) | (~R992 & Bin) | (R992 & ~((correct0  ^ Q) & ~Bin));
// reg_t Bin = Bout1024 ;
// .
// .
// .
// //Block 1055
// reg_t Bout1055 = ((~(R1023 ^ (correct31 ^ Q)) & Bin) | (~R990 & (correct31 ^ Q)));
// reg_t Rem31 = ((~R1023 & (correct31 ^ Q)) | ((correct31 ^ Q) & Bin) | (~R1023 & Bin) | (R1023 & ~(correct31 ^ Q) & ~Bin));



// Remx= ((Rem31) | (Rem30) | (Rem29) | (Rem28) | (Rem27) | (Rem26) | (Rem25) | (Rem24) | (Rem23) | (Rem22) | (Rem21) | (Rem20) | (Rem19) | (Rem18) | (Rem17) | (Rem16) | (Rem15) | (Rem14) | (Rem13) | (Rem12) | (Rem11) | (Rem10) | (Rem9) | (Rem8) | (Rem7) | (Rem6) | (Rem5) | (Rem4) | (Rem3) | (Rem2) | (Rem1) | (Rem0));

// WRITE_RD(sext_xlen(Remx));
// This line below should be removed in the next version when remx is implemented
WRITE_RD(sext_xlen(RS1 ^ RS2));
