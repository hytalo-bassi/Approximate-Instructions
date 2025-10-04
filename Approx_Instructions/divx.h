// This instruction is incomplete. In the near future we are going to 
// implement it properly, but now we will just import the addx WRITE_RD

// //Divx - 64X32
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
// Quoc = ((Quoc31) | (Quoc30) | (Quoc29) | (Quoc28) | (Quoc27) | (Quoc26) | (Quoc25) | (Quoc24) | (Quoc23) | (Quoc22) | (Quoc21) | (Quoc20) | (Quoc19) | (Quoc18) | (Quoc17) | (Quoc16) | (Quoc15) | (Quoc14) | (Quoc13) | (Quoc12) | (Quoc11) | (Quoc10) | (Quoc9) | (Quoc8) | (Quoc7) | (Quoc6) | (Quoc5) | (Quoc4) | (Quoc3) | (Quoc2) | (Quoc1) | (Quoc0));

// WRITE_RD(sext_xlen(Quoc));
// This line below should be removed in the next version when remx is implemented

WRITE_RD(sext_xlen(RS1 ^ RS2));
